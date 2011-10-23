from .base import  BaseReporter, MultiprocessReporterBase, LogOutputMixin, JSONFileOutputMixin


__author__ = 'boaz'

class LogReporter(LogOutputMixin,BaseReporter):
    __doc__ = """ Log based reporter. Will report on demand (when LogReporter.report is called) or periodically
        (use LogReporter.start_auto_report)
    """ + LogOutputMixin.__param_doc__


    pass


class MultiProcessLogReporter(LogOutputMixin,MultiprocessReporterBase):
    __doc__ = """
        Similar to :class:`LogReporter`, but supports collecting data from multiple processes.

        
    """ + LogOutputMixin.__param_doc__ + MultiprocessReporterBase.__param_doc__

    pass


class JSONFileReporter(JSONFileOutputMixin,BaseReporter):
    __doc__ = """
        Reports to a file in a JSON format.
    """ +  JSONFileOutputMixin.__param_doc__




    pass



class MultiProcessJSONFileReporter(JSONFileOutputMixin,MultiprocessReporterBase):
    __doc__ = """
        Similar to :class:`JSONFileReporter`, but supports collecting data from multiple processes.
    """+ JSONFileOutputMixin.__param_doc__ + MultiprocessReporterBase.__param_doc__

    pass
