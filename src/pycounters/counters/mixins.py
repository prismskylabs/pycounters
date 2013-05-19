from ..utils.timer import ThreadLocalTimer


class AutoDispatch(object):
    """ a mixin to wire up events to functions based on the property parameter. Anything without a match will be
        ignored.
        function signature is:
        def _report_event_PROPERTY(name, param)

    """

    def __init__(self, *args, **kwargs):
        super(AutoDispatch, self).__init__(*args, **kwargs)
        dispatch_dict = dict()
        for k in dir(self):
            if k.startswith("_report_event_"):
                # have a a handler, wire it up
                dispatch_dict[k[len("_report_event_"):]] = getattr(self, k)

        self.dispatch_dict = dispatch_dict

    def _report_event(self, name, property, param):
        handler = self.dispatch_dict.get(property)
        if handler:
            handler(name, param)


class TimerMixin(AutoDispatch):

    def __init__(self, *args, **kwargs):
        self.timer = None
        super(TimerMixin, self).__init__(*args, **kwargs)

    def _report_event_start(self, name, param):
        if not self.timer:
            self.timer = ThreadLocalTimer()

        self.timer.start()

    def _report_event_end(self, name, param):
        self._report_event(name, "value", self.timer.stop())


class TriggerMixin(AutoDispatch):
    """ translates end events to 1-valued events. Effectively counting them.
    """

    def _report_event_end(self, name, param):
        self._report_event(name, "value", 1L)
