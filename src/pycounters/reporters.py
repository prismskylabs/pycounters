import threading
from .base import GLOBAL_REGISTRY
import time
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
    
    def _output_report(self,values):
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

    def _output_report(self,values):
        logs = sorted(values.iteritems(),cmp=lambda a,b: cmp(a[0],b[0]))

        for k,v in logs:
            self.logger.info("%s %s",k,v)

