import threading
from ..base import GLOBAL_REGISTRY
import time
import tcpcollection

__author__ = 'boaz'


class BaseReporter(object):


    def __init__(self):
        self._auto_reporting_cycle = None
        self._auto_reporting_active = threading.Event()
        self._auto_reporting_thread = threading.Thread(target=self._auto_reporting_thread_target)
        self._auto_reporting_thread.daemon = True
        self._auto_reporting_thread.start()

    def report(self):
        """ Collects a report from the counters and outputs it
        """
        values = GLOBAL_REGISTRY.get_values()
        self._output_report(values)
    
    def _output_report(self,counter_values_col):
        raise NotImplementedError("Implement _output_report in a subclass.")


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
                time.sleep(self._auto_reporting_cycle)
            except Exception as e:
                try:
                    self._handle_background_error(e)
                except:
                    pass

class ReportingRole(object):
    LEADER_ROLE = 0
    NODE_ROLE = 1
    AUTO_ROLE = 2


class MultiprocessReporterBase(BaseReporter):
    """
        A base class to multiprocess aware reporter.
    """



    def __init__(self,collecting_address="",collecting_port=760907,debug_log=None,role=ReportingRole.AUTO_ROLE,
                 timeout_in_sec=120):
        """
            collecting_address = address of the machine data should be collected on.
            collecing_port = port of collecting process
            role = role of current process, set to AUTO for auto leader election
        """
        super(MultiprocessReporterBase,self).__init__()
        self.debug_log= debug_log
        self.leader = tcpcollection.CollectingLeader(collecting_address,collecting_port,debug_log=debug_log)
        self.node = tcpcollection.CollectingNode(
                self.node_get_values,
                self.node_io_error_callback,
                address=collecting_address,port=collecting_port,debug_log=debug_log)

        self.role = role
        self.actual_role = self.role
        self.timeout_in_sec=timeout_in_sec

        self.init_role()

    def init_role(self):
        if self.role == ReportingRole.LEADER_ROLE:
            self.leader.try_to_lead(throw=True)
        elif self.role == ReportingRole.NODE_ROLE:
            self.node.connect_to_leader(timeout_in_sec=self.timeout_in_sec)
        elif self.role == ReportingRole.AUTO_ROLE:
            self.log("Role is set to auto. Electing a leader.")
            (status, last_node_attempt_error, last_leader_attempt_error) =\
                tcpcollection.elect_leader(self.node, self.leader, timeout_in_sec=self.timeout_in_sec)

            if status:
                self.actual_role = ReportingRole.LEADER_ROLE
            else:
                self.actual_role = ReportingRole.NODE_ROLE
            self.log("Leader ellected. My Role is: %s", self.actual_role)

        # and now start the node for this process, if leading
        if self.actual_role == ReportingRole.LEADER_ROLE:
            self.node.connect_to_leader()

    def log(self,*args,**kwargs):
        if self.debug_log:
            self.debug_log.debug(*args,**kwargs)


    def report(self):
        """ outputs a report on leader process. O.w. a no-op
        """
        if self.actual_role == ReportingRole.LEADER_ROLE:
            values = self.leader_collect_values()
            self._output_report(values)


    def leader_collect_values(self):
        return self.leader.collect_from_all_nodes()

    def node_get_values(self):
        return GLOBAL_REGISTRY.get_values();

    def node_io_error_callback(self,err):
        self.log("Received an IO Error. Re-applying role")
        self.init_role()


    def shutdown(self):
        self.node.close()
        self.leader.stop_leading()







class LogReporter(BaseReporter):
    """ Log based reporter. Will report on demand (when LogReporter.report is called) or periodically
        (use LogReporter.start_auto_report)
    """


    def __init__(self,output_log):
        """ output will be logged to output_log
        """
        super(LogReporter,self).__init__()
        self.logger = output_log

    def _handle_background_error(self,e):
        self.logger.exception(e)

    def _output_report(self,counter_values_col):
        logs = sorted(counter_values_col.values.iteritems(),cmp=lambda a,b: cmp(a[0],b[0]))

        for k,v in logs:
            self.logger.info("%s %s",k,v)


