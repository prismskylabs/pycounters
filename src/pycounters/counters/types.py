from copy import copy
from ..base import THREAD_DISPATCHER
from .base import BaseCounter, BaseWindowCounter
from .mixins import AutoDispatch, TimerMixin, TriggerMixin
from .values import AccumulativeCounterValue, AverageCounterValue,\
    MinCounterValue, MaxCounterValue

__author__ = 'boaz'


class TotalCounter(AutoDispatch, BaseCounter):
    """ Counts the total of events' values.
    """

    def __init__(self, name, events=None):
        self.value = None
        super(TotalCounter, self).__init__(name, events=events)

    def _get_value(self):
        return AccumulativeCounterValue(self.value)

    def _report_event_value(self, name, value):

        if self.value:
            self.value += value
        else:
            self.value = long(value)

    def _clear(self):
        self.value = 0L


class AverageWindowCounter(AutoDispatch, BaseWindowCounter):
    """ Calculates a running average of arbitrary values """

    def _get_value(self):
        super(AverageWindowCounter, self)._get_value()
        if not self.values:
            v = None
        else:
            v = sum(self.values, 0.0) / len(self.values)

        return AverageCounterValue(v, len(self.values))


class FrequencyCounter(TriggerMixin, BaseWindowCounter):
    """ Use to count the frequency of some occurrences in a sliding window. Occurrences can be reported directly
        via a value event (X occurrences has happened now) or via an end event which will be interpreted as a single
        occurrence.
    """

    def _get_value(self):
        super(FrequencyCounter, self)._get_value()
        if not self.values or len(self.values) < 1:
            return AccumulativeCounterValue(0.0)
        return AccumulativeCounterValue(sum(self.values, 0.0) / (self._get_current_time() - self.times[0]))


class WindowCounter(TriggerMixin, BaseWindowCounter):
    """ Counts the number of end events in a sliding window """
    def _get_value(self):
        super(WindowCounter, self)._get_value()
        if not self.values or len(self.values) < 1:
            return AccumulativeCounterValue(0.0)
        return AccumulativeCounterValue(sum(self.values, 0.0))


class MaxWindowCounter(AutoDispatch, BaseWindowCounter):
    """ Counts maximum of events values in window """
    def _get_value(self):
        super(MaxWindowCounter, self)._get_value()
        if not self.values:
            return MaxCounterValue(None)
        val = max(self.values)
        return MaxCounterValue(float(val))


class MinWindowCounter(AutoDispatch, BaseWindowCounter):
    """ Counts minimum of events values in window """
    def _get_value(self):
        self._trim_window()
        if not self.values:
            return MinCounterValue(None)
        val = min(self.values)
        return MinCounterValue(float(val))


class AverageTimeCounter(TimerMixin, AverageWindowCounter):
    """ Counts the average time between start and end events
    """
    pass


class EventCounter(TriggerMixin, BaseCounter):
    """ Counts the number of times an end event has fired.
    """

    def __init__(self, name, events=None):
        self.value = None
        super(EventCounter, self).__init__(name, events=events)

    def _get_value(self):
        return AccumulativeCounterValue(self.value)

    def _report_event_value(self, name, value):

        if self.value:
            self.value += value
        else:
            self.value = long(value)

    def _clear(self):
        self.value = 0L


class ValueAccumulator(AutoDispatch, BaseCounter):
    """ Captures all named values it gets and accumulates them.
        Also allows rethrowing them, prefixed with their name."""

    def __init__(self, name, events=None):
        self.accumulated_values = dict()
        # forces the object not to accumulate values. Used when the object itself is raising events
        self._ignore_values = False

        super(ValueAccumulator, self).__init__(name, events=events)

    def _report_event_value(self, name, value):
        if self._ignore_values:
            return
        cur_value = self.accumulated_values.get(name)
        if cur_value:
            cur_value += value
        else:
            cur_value = value
        self.accumulated_values[name] = cur_value

    def _get_value(self):
        return copy(self.accumulated_values)

    def _clear(self):
        self.accumulated_values.clear()

    def raise_value_events(self, clear=False):
        """ raises accumuated values as value events. """
        with self.lock:
            self._ignore_values = True
            try:
                for k, v in self.accumulated_values.iteritems():
                    THREAD_DISPATCHER.dispatch_event(self.name + "." + k, "value", v)
            finally:
                self._ignore_values = True

            if clear:
                self._clear()
