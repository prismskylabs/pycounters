from time import time
from threading import local as threading_local


class Timer(object):
    """ a thread specific timer. """

    def _get_current_time(self):
        return time()

    def start(self):
        """ start timing """
        self.start_time = self._get_current_time()
        if not hasattr(self, "accumulated_time"):
            self.accumulated_time = 0.0

    def stop(self):
        """ stops the timer returning accumulated time so far. Also clears out the accumulated time. """
        t = self.pause()
        self.accumulated_time = 0.0
        return t

    def pause(self):
        """ pauses the time returning accumulated time so far """
        ct = self._get_current_time()
        delta = ct - self.start_time
        self.accumulated_time += delta

        return self.accumulated_time

    def get_accumulated_time(self):
        if not hasattr(self, "accumulated_time"):
                self.accumulated_time = 0.0
        return self.accumulated_time


class ThreadLocalTimer(threading_local, Timer):
    pass
