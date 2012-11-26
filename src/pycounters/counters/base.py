from exceptions import NotImplementedError
from pycounters.base import BaseListener
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
