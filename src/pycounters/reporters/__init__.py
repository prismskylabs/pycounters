from .base import  BaseReporter


__author__ = 'boaz'


class LogReporter(BaseReporter):
    """ Log based reporter.
    """

    def __init__(self, output_log=None):
        """ output will be logged to output_log
            :param output_log: a python log object to output reports to.
        """
        super(LogReporter, self).__init__()
        self.logger = output_log

    def output_values(self, counter_values):
        logs = sorted(counter_values.iteritems(), cmp=lambda a, b: cmp(a[0], b[0]))

        for k, v in logs:
            if not (k.startswith("__") and k.endswith("__")):   # don't output __node_reports__ etc.
                self.logger.info("%s %s", k, v)
