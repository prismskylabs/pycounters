from .base import  BaseReporter, MultiprocessReporterBase, LogOutputMixin, JSONFileOutputMixin


__author__ = 'boaz'

class LogReporter(LogOutputMixin,BaseReporter):
    """ Log based reporter. Will report on demand (when LogReporter.report is called) or periodically
        (use LogReporter.start_auto_report)
    """

    pass


class MultiProcessLogReporter(LogOutputMixin,MultiprocessReporterBase):
    """
        Similar to LogReporter, but supports collecting data from multiple processes.
    """

    pass


class JSONFileReporter(JSONFileOutputMixin,BaseReporter):
    """
        Reports to a file in a JSON format. The file name is indicated by the output_file keyword argument
        to __init__
    """

    pass



