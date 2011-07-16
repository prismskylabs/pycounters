from SocketServer import BaseRequestHandler, TCPServer
from itertools import repeat
import threading
import multiprocessing
import pickle
import socket
import time
import traceback
import itertools

class ExplicitRequestClosingTCPServer(TCPServer):
    """ A tcp server that doesn't automatically shutdown incoming requests
    """

    def process_request(self, request, client_address):
        """Call finish_request.

            Different from parent by that that it doesn't shutdown the request
        """
        self.finish_request(request, client_address)


class CollectingNodeProxy(BaseRequestHandler):
    """ a proxy to the CollectingNode. Used by collecting leader to get info from collection Node.
    """



    # Default buffer sizes for rfile, wfile.
    # We default rfile to buffered because otherwise it could be
    # really slow for large data (a getc() call per byte); we make
    # wfile unbuffered because (a) often after a write() we want to
    # read and we need to flush the line; (b) big writes to unbuffered
    # files are typically optimized by stdio even when big reads
    # aren't.
    rbufsize = 0
    wbufsize = 0

    def __init__(self,leader,request,client_address,server,debug_log=None):
        self.leader=leader
        self.debug_log=debug_log
        BaseRequestHandler.__init__(self,request,client_address,server)

    def log(self,*args,**kwargs):
       if self.debug_log:
           self.debug_log.debug(*args,**kwargs)

    ### BaseRequestHandler functions
    def setup(self):
        self.connection = self.request
        self.rfile = self.connection.makefile('rb', self.rbufsize)
        self.wfile = self.connection.makefile('wb', self.wbufsize)

    def handle(self):
        try:
            self.log("Handling an incoming registration request. Asking for node name.")
            node_id = self.receive()
            self.log("Connected to node %s" ,node_id)
            self.id = node_id
            self.leader.register_node_proxy(self)
            self.send("ack")
        except Exception as e:
            st = traceback.format_exc()
            self.log("Got an exception while dealing with an incoming request: %s, st:",e,st)
            self.request.close()
            raise


    def finish(self):
        pass

    ### Collecting Proxy functions
    def send(self,data):
        pickle.dump(data,self.wfile,pickle.HIGHEST_PROTOCOL)
        self.wfile.flush()


    def receive(self):
        return pickle.load(self.rfile)

    def send_and_receive(self,data):
        self.send(data)
        return self.receive()

    def close(self):
        if not self.wfile.closed:
            self.wfile.flush()
        self.wfile.close()
        self.rfile.close()
        self.connection.close()



class CollectingLeader(object):
    """
        A class which sets up a socket server for collecting reports from CollectingNodes
    """

    def __init__(self,address ="",port=760907,debug_log=None):
        self.address=address
        self.port = port
        self.debug_log = debug_log
        self.lock = threading.RLock()
        self.node_proxies = dict()
        self.tcp_server = None
        self.leading = False


    def try_to_lead(self,throw=False):
        """ tries to claim leader ship position. Returns none on success, an error message on failure
        """
        try:
            self.tcp_server = ExplicitRequestClosingTCPServer((self.address, self.port),
                                                    self.make_stream_request_handler,bind_and_activate=False)
            self.allow_reuse_address = True
            try:
                self.tcp_server.server_bind()
                self.tcp_server.server_activate()
            except:
                self.tcp_server.server_close()
                raise

        except IOError as e:
            self.log("Failed to setup TCP Server %s:%s . Error: %s",self.address,self.port,e)
            if throw:
                raise
            return str(e)

        self.log("Successfully gained leader ship. Start responding to nodes")
        self.leading = True
        def target():
            try:
                self.log('serving thread is running')
                self.tcp_server.serve_forever()
                self.log('serving thread stoppinng')
            except Exception as e:
                self.log("Server had an error: %s",e)

        t=threading.Thread(target=target)
        t.daemon=True
        t.start()

            

        return None


    def stop_leading(self):
        if self.leading:
            self.tcp_server.shutdown()
            self.tcp_server.server_close()
        with self.lock:
            for node in self.node_proxies.itervalues():
                self.log("Closing proxy for %s",node.id)
                node.close()

            self.node_proxies = {}
        

    def send_to_all_nodes(self,data):
        with self.lock:
            for node in self.node_proxies:
                try:
                    node.send(data)
                except IOError as e:
                    self.log("Get an error when sending to node %s:\nerror:%s,\ndata:%s",node.id,e,data)



    def collect_from_all_nodes(self):
        """ returns a dictionary with answers from all nodes. Dictionary id is node id.
        """
        ret = {}
        with self.lock:
            error_nodes = []
            for node in self.node_proxies.itervalues():
                try:
                    ret[node.id]=node.send_and_receive("collect")
                except IOError as e:
                    self.log("Get an error when sending to node %s:\nerror:%s",node.id,e)
                    node.close()
                    error_nodes.append(node.id)

            for err_node in error_nodes:
                self.log("Removing node %s from collection",errnode)
                del self.node_proxies[err_node]

        return ret



    def log(self,*args,**kwargs):
        if self.debug_log:
            self.debug_log.debug(*args,**kwargs)

    def register_node_proxy(self,proxy):
        with self.lock:
            self.node_proxies[proxy.id]=proxy

    def make_stream_request_handler(self,request, client_address, server):
        """ Creates a CollectingNodeProxy
        """
        return CollectingNodeProxy(self,request,client_address,server,debug_log=self.debug_log)

_GLOBAL_COUNTER= itertools.count()

class CollectingNode(object):

    def __init__(self,collect_callback,io_error_callback,address="",port=60907,debug_log=None):
        """ collect_callback will be called to collect values
            io_error_callbakc is called when an io error ocours (the exception is passed as a param).
                NOTE: ** IT IS YOUR RESPONSIBILITY TO RE-Connect.
        """
        self.address=address
        self.port =port
        self.debug_log= debug_log
        self.collect_callback=collect_callback
        self.io_error_callback=io_error_callback
        self.background_thread=None
        self.id = self.gen_id()
        self._shutting_down=False


    def gen_id(self):
        id = _GLOBAL_COUNTER.next()
        return socket.getfqdn()+"_"+str(multiprocessing.current_process().ident)+"_"+str(id)

    def try_connecting_to_leader(self,throw=False):
        """ tries to find an elected leader. Returns None on success , error message on failure
        """

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(None)
        try:
            self.socket.connect((self.address, self.port))
        except  IOError as e:
            self.log("%s: Failed to find leader on %s:%s . Error: %s",self.id,self.address,self.port,e)
            if throw:
                raise
            return str(e)

        self.rfile = self.socket.makefile('rb', 1)
        self.wfile = self.socket.makefile('wb', 1)
        self.send(self.id)
        if (self.receive()!="ack"):
            raise Exception("Failed to get ack from leader.")
        return None

    def connect_to_leader(self,timeout_in_sec=120):
        """ tries repeatedly to connect to leader
        """
        wait_times = [0.1,0.2]
        wait_times.extend(repeat(1,int(timeout_in_sec)))
        last_node_attempt_error = None
        for cur_itr in range(len(wait_times)):
            last_node_attempt_error = self.try_connecting_to_leader()
            if not last_node_attempt_error:
                # success!
                self.start_background_receive()
                return

            time.sleep(wait_times[cur_itr])



        # if we got here things are bad..
        raise Exception("Failed to ellect a leader. Tried %s times. Last node attempt error: %s." %
                        (cur_itr,last_node_attempt_error)
                        )

    def start_background_receive(self):
        def target():
            try:
                self.log('Cmd exec thread is running')
                self.execute_commands()
                self.log('Cmd exec thread stoppinng')
            except Exception as e:
                st = traceback.format_exc()
                self.log("Cmd exec had an error (id:%s): %s\n,STACK TRACE: %s",self.id,e,st)

        self.background_thread=threading.Thread(target=target)
        self.background_thread.daemon=True
        self.background_thread.start()

        return


    def log(self,*args,**kwargs):
        if self.debug_log:
            self.debug_log.debug(*args,**kwargs)


    def send(self,data):
        pickle.dump(data,self.wfile,pickle.HIGHEST_PROTOCOL)
        self.wfile.flush()

    def receive(self):
        return pickle.load(self.rfile)

    def get_command_and_execute(self):
        cmd = self.receive()
        self.log("Got %s", cmd)
        if cmd=="quit":
            self.close()
            return False
        if cmd=="collect":
            self.log("'%s': Collecting.",self.id)
            v=self.collect_callback()
            self.send(v)
            self.log("'%s': Done collecting.",self.id)
            return True

        if cmd=="wait":
            return True

    def execute_commands(self):
        go =True
        while go and not self._shutting_down:
            try:
                go=self.get_command_and_execute()
            except (IOError,EOFError) as e:
                self.log("%s: Got an IOError/EOFError %s",self.id,e)
                self.wfile.close()
                self.rfile.close()
                try:
                    #explicitly shutdown.  socket.close() merely releases
                    #the socket and waits for GC to perform the actual close.
                    self.socket.shutdown(socket.SHUT_WR)
                except socket.error:
                    pass #some platforms may raise ENOTCONN here
                self.socket.close()
                if not self._shutting_down:
                    self.log("%s: Call io_error_callback.",self.id)
                    self.io_error_callback(e)
                go=False


    def close(self):
        self.log("%s: closing..",self.id)
        self._shutting_down=True
        if not self.wfile.closed:
            self.wfile.flush()
        self.wfile.close()
        self.rfile.close()
        self.socket.close()



def elect_leader(collecting_node,collecting_leader,timeout_in_sec=120):
    """ initiates the process of electing a leader between running processes. All processes are assumed to call this
        function whenever in doubt of the current leader. This can be due to network issues, or at startup.
        Protocol:
            - Try to connect to an existing leader.
            - Try to become a leader.
            - Wait (increasingly long, 0.1,0.2,0.5,0.5,1,1,1)
            - If got here scream!

        Input - configured collecting_node and collecting leader.

        returns:
            (Status,last_node_attempt_error,last_leader_attempt_error)
                Status= True if leader (collecting_leader is now answering requests), false if not (collecting_node is
                    connected to ellected leader)

    """
    wait_times = [0.1,0.2]
    wait_times.extend(repeat(1,int(timeout_in_sec)))
    last_node_attempt_error = None
    last_leader_attempt_error = None
    for cur_itr in range(len(wait_times)):
        last_node_attempt_error = collecting_node.try_connecting_to_leader()
        if not last_node_attempt_error:
            # success!
            collecting_node.start_background_receive()
            return (False,last_node_attempt_error,last_leader_attempt_error)

        last_leader_attempt_error = collecting_leader.try_to_lead()
        if not last_leader_attempt_error:
            # success!
            return (True,last_node_attempt_error,last_leader_attempt_error)

        time.sleep(wait_times[cur_itr])


    # if we got here things are bad..
    raise Exception("Failed to ellect a leader. Tried %s times. Last node attempt error: %s. Last leader attempt error: %s." %
                    (cur_itr,last_node_attempt_error,last_leader_attempt_error)
                    )   

