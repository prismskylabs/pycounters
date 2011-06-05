from collections import deque
from copy import copy
from threading import RLock, local as threading_local
from time import time
from pycounters.base import THREAD_DISPATCHER, BaseListener

__author__ = 'boaz'


class BaseCounter(BaseListener):



    def __init__(self,name):
        self.name=name
        self.lock = RLock()

    def report_event(self,name,property,param):
        """ reports an event to this counter """
        with self.lock:
            self._report_event(name,property,param)

    def get_value(self):
        with self.lock:
            return self._get_value()

    def clear(self,dump=True):
        with self.lock:
            self._clear()

    def _report_event(self,name,property,param):
        """ implement this in sub classes """
        raise NotImplementedError("_report_event is not implemented")

    def _get_value(self):
        """ implement this in sub classes """
        raise NotImplementedError("_get_value is not implemented")

    def _clear(self):
        """ implement this in sub classes """
        raise NotImplementedError("_clear is not implemented")


class AutoDispatch(object):
    """ a mixing to wire up events to functions based on the property parameter. Anything without a match will be
        ignored.
        function signature is:
        def _report_event_PROPERTY(name,param)

    """


    def __init__(self,*args,**kwargs):
        super(AutoDispatch,self).__init__(*args,**kwargs)
        dispatch_dict = dict()
        for k in dir(self):
            if k.startswith("_report_event_"):
                # have a a handler, wire it up
                dispatch_dict[k[len("_report_event_"):]]=getattr(self,k)

        self.dispatch_dict = dispatch_dict



    def _report_event(self,name,property,param):
        handler = self.dispatch_dict.get(property)
        if handler:
            handler(name,param)



class Timer(object):
    """ a thread specific timer. """

    def _get_current_time(self):
        return time()

    def start(self):
        """ start timing """
        self.start_time = self._get_current_time()
        if not hasattr(self,"accumulated_time"):
            self.accumulated_time = 0.0

    def stop(self):
        """ stops the timer returning accumulated time so far. Also clears out the accumaulated time. """
        t = self.pause()
        self.accumulated_time = 0.0
        return t

    def pause(self):
        """ pauses the time returning accumulated time so far """
        ct = self._get_current_time()
        delta = ct-self.start_time
        self.accumulated_time += delta

        return self.accumulated_time

    def get_accumulated_time(self):
        if not hasattr(self,"accumulated_time"):
                self.accumulated_time = 0.0
        return self.accumulated_time

class ThreadLocalTimer(threading_local,Timer):
    pass

class TimerMixin(AutoDispatch):


    def __init__(self,*args,**kwargs):
        self.timer=None
        super(TimerMixin,self).__init__(*args,**kwargs)


    def _report_event_start(self,name,param):
        if not self.timer:
            self.timer = ThreadLocalTimer()
            
        self.timer.start()

    def _report_event_end(self,name,param):
        self._report_event(name,"value",self.timer.stop())




class TriggerMixin(AutoDispatch):
    """ translates end events to 1-valued events. Effectively counting them.
    """

    def _report_event_end(self,name,param):
        self._report_event(name,"value",1L)


class EventCounter(TriggerMixin,BaseCounter):
    """ Counting the number of times an end event has fired.
    """

    def __init__(self,name):
        self.value = 0L
        super(EventCounter,self).__init__(name)


    def _get_value(self):
        return self.value;

    def _report_event_value(self,name,value):

        if self.value:
            self.value += value
        else:
            self.value = long(value)


    def _clear(self):
        self.value = 0L


class AverageWindowCounter(AutoDispatch,BaseCounter):
    """ Calculating a running average of arbitrary values """

    def __init__(self,name,window_size=300.0):
        super(AverageWindowCounter,self).__init__(name)
        self.window_size=window_size
        self.values = deque()
        self.times = deque()


    def _clear(self):
        self.values.clear()
        self.times.clear()

    def _get_value(self):
        self._trim_window()
        if not self.values:
            return 0.0
        return sum(self.values, 0.0) / len(self.values)

    def _trim_window(self):
        window_limit = self._get_current_time()-self.window_size
        # trim old data
        while self.times and self.times[0] < window_limit:
            self.times.popleft()
            self.values.popleft()


    def _report_event_value(self,param,value):
        self._trim_window()
        self.values.append(value)
        self.times.append(self._get_current_time())


    def _get_current_time(self):
        return time()


class FrequencyCounter(TriggerMixin,AverageWindowCounter):
    """ Counts the frequency of end events in the last five minutes
    """

    def _get_value(self):
        self._trim_window()
        if not self.values or len(self.values)<2:
            return 0.0
        return sum(self.values, 0.0) / (self._get_current_time()-self.times[0])



class AverageTimeCounter(TimerMixin,AverageWindowCounter):
    """ Counts the average time between start and end events
    """
    
    pass



class ValueAccumulator(AutoDispatch,BaseCounter):
    """ Captures all named values it gets and accumulates them. Also allows rethrowing them, prefixed with their name."""

    def __init__(self,*args,**kwargs):
        self.accumulated_values=dict()
        # forces the object not to accumulate values. Used when the object itself is raising events
        self._ignore_values = False

        super(ValueAccumulator,self).__init__(*args,**kwargs)


    def _report_event_value(self,name,value):
        if self._ignore_values: return
        cur_value = self.accumulated_values.get(name)
        if cur_value:
            cur_value += value
        else:
            cur_value = value
        self.accumulated_values[name]=cur_value


    def _get_value(self):
        return copy(self.accumulated_values)

    def _clear(self):
        self.accumulated_values.clear()


    def raise_value_events(self,clear=False):
        """ raises accumuated values as value events. """
        with self.lock:
            self._ignore_values = True
            try:
                for k,v in self.accumulated_values.iteritems():
                    THREAD_DISPATCHER.disptach_event(self.name + "." + k,"value",v)
            finally:
                self._ignore_values = True

            if clear:
                self._clear()



class ThreadTimeCategorizer(BaseListener):
    """ A class to divide the time spent by thread across multiple categories. Categories are mutually exclusive. """

    def __init__(self,name,categories,timer_class=Timer):
        super(ThreadTimeCategorizer,self).__init__()
        self.name = name
        self.category_timers = dict()
        self.timer_stack = list() # a list of strings of paused timers
        for cat in categories:
            self.category_timers[cat]=timer_class()


    def report_event(self,name,property,param):
        if property == "start":
            cat_timer = self.category_timers.get(name)
            if not cat_timer:
                return

            if self.timer_stack:
                self.timer_stack[-1].pause()


            cat_timer.start()
            self.timer_stack.append(cat_timer)

        elif property == "end":
            cat_timer = self.category_timers.get(name) # if all went well it is there...
            if not cat_timer:
                return
            cat_timer.pause()
            self.timer_stack.pop()
            if self.timer_stack:
                self.timer_stack[-1].start() # continute last paused timer


   
    def raise_value_events(self,clear=False):
        """ raises category total time as value events. """
        for k,v in self.category_timers.iteritems():
            THREAD_DISPATCHER.disptach_event(self.name + "." + k,"value",v.get_accumulated_time())

        if clear:
            self.category_timers.clear()

