from .. import base
from .timer import Timer


class ThreadTimeCategorizer(base.BaseListener):
    """ A class to divide the time spent by thread across multiple categories. Categories are mutually exclusive. """

    def __init__(self, name, categories, timer_class=Timer):
        super(ThreadTimeCategorizer, self).__init__()
        self.name = name
        self.category_timers = dict()
        self.timer_stack = list()  # a list of strings of paused timers
        for cat in categories:
            self.category_timers[cat] = timer_class()

    def get_times(self):
        ret = []
        for k, v in self.category_timers.iteritems():
            ret.append((self.name + "." + k, v.get_accumulated_time()))
        return ret

    def report_event(self, name, property, param):
        if property == "start":
            cat_timer = self.category_timers.get(name)
            if not cat_timer:
                return

            if self.timer_stack:
                self.timer_stack[-1].pause()

            cat_timer.start()
            self.timer_stack.append(cat_timer)

        elif property == "end":
            cat_timer = self.category_timers.get(name)  # if all went well it is there...
            if not cat_timer:
                return
            cat_timer.pause()
            self.timer_stack.pop()
            if self.timer_stack:
                self.timer_stack[-1].start()  # continute last paused timer

    def raise_value_events(self, clear=False):
        """ raises category total time as value events. """
        for k, v in self.get_times():
            base.THREAD_DISPATCHER.dispatch_event(k, "value", v)

        if clear:
            self.category_timers.clear()
