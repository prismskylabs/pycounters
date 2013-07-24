from collections import deque
from exceptions import NotImplementedError
from time import time
from ..base import BaseListener
from threading import RLock


class BaseCounter(BaseListener):

    def __init__(self, name, events=None):
        """
           name - name of counter
           events - events this counter should count. can be
                None - defaults to events called the same as counter name
                [event, event, ..] - a list of events to listen to
        """
        self.name = name
        if events is None:
            events = [name]
        super(BaseCounter, self).__init__(events=events)

        self.lock = RLock()

    def report_event(self, name, property, param):
        """ reports an event to this counter """
        with self.lock:
            self._report_event(name, property, param)

    def get_value(self):
        """
         gets the value of this counter
        """
        with self.lock:
            return self._get_value()

    def clear(self, dump=True):
        """ Clears the stored information
        """
        with self.lock:
            self._clear()

    def _report_event(self, name, property, param):
        """ implement this in sub classes """
        raise NotImplementedError("_report_event is not implemented")

    def _get_value(self):
        """ implement this in sub classes """
        raise NotImplementedError("_get_value is not implemented")

    def _clear(self):
        """ implement this in sub classes """
        raise NotImplementedError("_clear is not implemented")


class BaseWindowCounter(BaseCounter):
    """ A base class for counters that aggregate data based on a sliding window """

    def __init__(self, name, window_size=300.0, events=None):
        super(BaseWindowCounter, self).__init__(name, events=events)
        self.window_size = window_size
        self.values = deque()
        self.times = deque()

    def _clear(self):
        self.values.clear()
        self.times.clear()

    def _get_value(self):
        """ override this function with your aggregation logic. call base class for data trimming.  """
        self._trim_window()

    def _trim_window(self):
        window_limit = self.get_current_window_start_time()
        # trim old data
        while self.times and self.times[0] < window_limit:
            self.times.popleft()
            self.values.popleft()

    def _report_event_value(self, param, value):
        self._trim_window()
        self.values.append(value)
        self.times.append(self._get_current_time())

    def _get_current_time(self):
        return time()

    def get_current_window_start_time(self):
        return self._get_current_time() - self.window_size
