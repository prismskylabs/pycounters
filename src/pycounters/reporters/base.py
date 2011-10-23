from exceptions import NotImplementedError, Exception
import threading
import time
import os
import json
import fcntl
from pycounters.base import GLOBAL_REGISTRY, CounterValueCollection
from . import tcpcollection

__author__ = 'boaz'


class BaseReporter(object):


    def __init__(self,*args,**kwargs):
        self._auto_reporting_cycle = None
        self._auto_reporting_active = threading.Event()
        self._auto_reporting_thread = threading.Thread(target=self._auto_reporting_thread_target)
        self._auto_reporting_thread.daemon = True
        self._auto_reporting_thread.start()

    def report(self):
        """ Collects a report from the counters and outputs it
        """
        values_col = GLOBAL_REGISTRY.get_values()
        self._output_report(values_col.values)

    def _output_report(self,counter_values):
         # raise NotImplementedError("Implement _output_report in a subclass.")
        pass

    def start_auto_report(self,seconds=300):
        """
        Start reporting in a background thread. Reporting frequency is set by seconds param.
        """
        self._auto_reporting_cycle = float(seconds)
        self._auto_reporting_active.set()

    def stop_auto_report(self):
        """ Stop auto reporting """
        self._auto_reporting_active.clear()


    def _handle_background_error(self,e):
        """ is called by backround reporting thread on error. It is highly recommended to implement this """
        pass

    def _auto_reporting_thread_target(self):
        def new_wait():
            self._auto_reporting_active.wait()
            return True
        while new_wait():
            try:
                self.report()
            except Exception as e:
                try:
                    self._handle_background_error(e)
                except:
                    pass

            time.sleep(self._auto_reporting_cycle)



class ReportingRole(object):
    LEADER_ROLE = 0
    NODE_ROLE = 1
    AUTO_ROLE = 2


class MultiprocessReporterBase(BaseReporter):
    """
        A base class to multiprocess aware reporter.

        Reporters inheriting from this base class need to implement _output_report. The values collection
        given to this function contains the aggregated value collection. Original per node values are
        stored under the __original__ key.

    """

    __param_doc__ = """

        :param collecting_address: a tuple in the form of (server_name, port_number) for the different processes
            to communicate on. One of the processes running on server_name will be elected to collect values from
            all other processes. Processes not running on server_name will automatically connect to ones who do.

            collecting_address can also be a list of tuples of the above format. In this case the connection would be
            made on the first available address. In case the first address is not available, a periodical background
            test will be made for it's availability. As soon as it becomes available the collecting will be moved. This
            is useful for quick recycling of the monitored process as the main port previously used will not be
            immediately available.

            .. note: use an empty string "" as server_name for localhost.

    """

#        Some more info about how this works:
#            - every instance of this class has two components a node and a leader
#            - By default the instances auto elect an active leader upon start up or when the leader becomes
#                unavailable.
#            - The elected leader is actually responsible for collecting values from all nodes and outputting it.
#            - The nodes are supposed to deliver their report as a CounterValueCollection.
#            - The leader merges it and output it.



    def __init__(self,collecting_address=[("",60907),("",60906)],debug_log=None,role=ReportingRole.AUTO_ROLE,
                 timeout_in_sec=120,*args,**kwargs):
        """
            collecting_address = address of the machine data should be collected on.
            collecing_port = port of collecting process
            role = role of current process, set to AUTO for auto leader election
        """
        super(MultiprocessReporterBase,self).__init__(*args,**kwargs)
        self.debug_log= debug_log if debug_log else tcpcollection._noplogger()
        self.lock = threading.RLock()
        self.collecting_address=tcpcollection.normalize_hosts_and_ports(collecting_address)
        self.leader =None
        self.node = None
        self.role = role
        self.actual_role = self.role
        self.timeout_in_sec=timeout_in_sec

        self.init_role()


    def _create_leader(self,collecting_addresses=None):
        if collecting_addresses is None:
            collecting_addresses = self.collecting_address
        return tcpcollection.CollectingLeader(hosts_and_ports=collecting_addresses,debug_log=self.debug_log)

    def _create_node(self,collecting_addresses=None):
        if collecting_addresses is None:
            collecting_addresses = self.collecting_address

        return tcpcollection.CollectingNode(
               self.node_get_values,
               self.node_io_error_callback,
               hosts_and_ports=collecting_addresses,debug_log=self.debug_log)

    def init_role(self):
        with self.lock:
            self.actual_role = None # mark things as unknown...

            if self.role == ReportingRole.LEADER_ROLE:
                self.leader= self._create_leader()
                self.leader.try_to_lead(throw=True)
                self.actual_role = ReportingRole.LEADER_ROLE
                self.node = self._create_node() ## create node for this process
                self.node.connect_to_leader()
            elif self.role == ReportingRole.NODE_ROLE:
                self.node = self._create_node()
                self.node.connect_to_leader(timeout_in_sec=self.timeout_in_sec)
                self.actual_role = ReportingRole.NODE_ROLE
            elif self.role == ReportingRole.AUTO_ROLE:
                self.node = self._create_node()
                self.leader= self._create_leader()
                self.debug_log.info("Role is set to auto. Electing a leader.")
                (status, last_node_attempt_error, last_leader_attempt_error) =\
                    tcpcollection.elect_leader(self.node, self.leader, timeout_in_sec=self.timeout_in_sec)

                if status:
                    self.actual_role = ReportingRole.LEADER_ROLE
                    self.node.connect_to_leader() ## node for current process.
                else:
                    self.actual_role = ReportingRole.NODE_ROLE

                self.debug_log.info("Leader elected. My Role is: %s", self.actual_role)

            if self.actual_role == ReportingRole.LEADER_ROLE:


                if self.leader.leading_level >0 :
                    # set an upgrading thread to try claim preferred leading settings

                    upgrading_thread=threading.Thread(target=self._auto_upgrade_server_level_target)
                    upgrading_thread.daemon=True
                    upgrading_thread.start()
                    

    def _try_upgrading_leader(self,potential_addresses):
        self.debug_log.debug("Trying to upgrade leadership")
        new_leader=self._create_leader(collecting_addresses=potential_addresses)
        status = new_leader.try_to_lead()
        if status is None:
            self.debug_log.info("New leader is established. Level is %s",new_leader.leading_level)
            with self.lock:
                self.leader.reconnect_nodes()
                self.leader.stop_leading()
                self.leader = new_leader

            return True

        return False




    def _auto_upgrade_server_level_target(self,wait_time=60):
        """ a target function for upgrading server level, if it happens to be too high..
        """
        while True:
            if self.actual_role != ReportingRole.LEADER_ROLE or self.leader.leading_level==0:
                self.debug_log.info("server upgrading stopped - I'm not a leader or leading level is 0")
                return

            potential_addresses = self.collecting_address[:self.leader.leading_level]


            if self.role == ReportingRole.AUTO_ROLE:
                # node is in auto_role... first figure out if the is some other leading available with a better
                # level...
                self.debug_log.debug("Trying to find a better leader")
                new_node = self._create_node(collecting_addresses=potential_addresses)
                status = new_node.try_connecting_to_leader(ping_only=True)
                if status is None:
                    ## some other leader exist with a higher order..

                    self.debug_log.info("Found a leader of a higher order. Switching to a node role")
                    with self.lock:
                        self.leader.reconnect_nodes()
                        self.leader.stop_leading()
                        self.leader = None
                        self.actual_role = ReportingRole.NODE_ROLE


                    return

            ## Node is either in auto role with no alternative leader
            ## or it has been designated as a leader. Both cases mean trying to upgrade leader
            self._try_upgrading_leader(potential_addresses)

            if self.leader.leading_level == 0:
                self.debug_log.debug("Highest level achieved. Stopping.")
                return


            self.debug_log.debug("Failed to upgrade to a higher level... waiting and trying again..")
            time.sleep(wait_time)


    def report(self):
        """ outputs a report on leader process. O.w. a no-op
        """
        if self.actual_role == ReportingRole.LEADER_ROLE:
            with self.lock:
                values = self.leader_collect_values()
                merged_values = self.merge_values(values)
                self._output_report(merged_values)


    def merge_values(self,values):
        merged_collection = CounterValueCollection()
        original_values = {}
        for node,report in values.iteritems():
            self.debug_log.debug("Merging report from %s",node)
            merged_collection.merge_with(report)
            original_values[node]=report.values

        res = merged_collection.values
        res["__node_reports__"]=original_values
        return res



    def leader_collect_values(self):
        return self.leader.collect_from_all_nodes()

    def node_get_values(self):
        return GLOBAL_REGISTRY.get_values()

    def node_io_error_callback(self,err):
        self.debug_log.warning("Received an IO Error. Re-applying role")
        self.init_role()


    def shutdown(self):
        with self.lock:
            self.actual_role=None
            if self.node:
                self.node.close()
                self.node = None
            if self.leader:
                self.leader.stop_leading()
                self.leader=None


class LogOutputMixin(object):
    """ a mixin to add outputting to a log.
    """

    __param_doc__ = """
        :param output_log: a python log object to output reports to.
    """

    def __init__(self,output_log=None,*args,**kwargs):
        """ output will be logged to output_log
        """
        super(LogOutputMixin,self).__init__(*args,**kwargs)
        self.logger = output_log

    def _handle_background_error(self,e):
        self.logger.exception(e)

    def _output_report(self,counter_values):
        super(LogOutputMixin,self)._output_report(counter_values) ## behave nice with other mixins
        logs = sorted(counter_values.iteritems(),cmp=lambda a,b: cmp(a[0],b[0]))

        for k,v in logs:
            if not (k.startswith("__") and k.endswith("__")): ## don't output __node_reports__ etc.
                self.logger.info("%s %s",k,v)


class JSONFileOutputMixin(object):
    """
        a mixin for output the collected reports to file in JSON format.
    """

    __param_doc__ = """
        :param output_file: a file name to which the reports will be written.
    """


    def __init__(self,output_file=None,*args,**kwargs):
        """ output will be logged to output_log
        """
        super(JSONFileOutputMixin,self).__init__(*args,**kwargs)
        self.output_file = output_file
        ## try to open the file now, just to see if it is possible and raise an exception if not
        self._output_report({"__initializing__" : True})


    def _output_report(self,counter_values):
        super(JSONFileOutputMixin,self)._output_report(counter_values) ## behave nice with other mixins
        JSONFileOutputMixin.safe_write(counter_values,self.output_file)


    @staticmethod
    def _lockfile(file):
        try:
            fcntl.flock(file, fcntl.LOCK_EX)
            return True
        except IOError, exc_value:
        #  IOError: [Errno 11] Resource temporarily unavailable
            if exc_value[0] == 11 or exc_value[0] == 35:
                return False
            else:
                raise

    @staticmethod
    def _unlockfile(file):
        fcntl.flock(file, fcntl.LOCK_UN)

    @staticmethod
    def safe_write(value,filename):
        """ safely writes value in a JSON format to file
        """
        fd=os.open(filename,os.O_CREAT | os.O_TRUNC | os.O_WRONLY)
        JSONFileOutputMixin._lockfile(fd)
        try:

            file=os.fdopen(fd,"w")
            json.dump(value,file)
        finally:
            JSONFileOutputMixin._unlockfile(fd)
            file.close()
        # fd is now close by the with clause


    @staticmethod
    def safe_read(filename):
       """ safely reads a value in a JSON format frome file
       """
       fd=os.open(filename,os.O_RDONLY)
       JSONFileOutputMixin._lockfile(fd)
       try:
           file=os.fdopen(fd,"r")
           return json.load(file)
       finally:
           JSONFileOutputMixin._unlockfile(fd)
           file.close()

        # fd is now close by the with clause

