from collections import deque
from copy import copy
from threading import RLock, local as threading_local
from time import time
from pycounters.base import THREAD_DISPATCHER, BaseListener
from typeinfo import MemberTypeInfo, TypedObject, NonNullable

__author__ = 'boaz'


class BaseCounter(TypedObject,BaseListener):

    name = MemberTypeInfo(type=basestring,nullable=False,none_on_init=True)

    lock = NonNullable(type=RLock().__class__) # RLock hides the actual class.
    

    def __init__(self,name,output_log=None,parent=None):
        self.initMembers()
        self.parent=parent
        self.output_log = output_log
        self.name=name

    def report_event(self,name,property,param):
        """ reports an event to this counter """
        if self.parent: self.parent.report_event(name,property,param)
        with self.lock:
            self._report_event(name,property,param)

    def get_value(self):
        with self.lock:
            return self._get_value()

    def clear(self,dump=True):
        with self.lock:
            if dump and self.output_log:
                self.output_log.info("Counter '%': %s",self.name,self.get_value())
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


    def __new__(cls,*args,**kwargs):
        r = super(AutoDispatch,cls).__new__(cls,*args,**kwargs)
        dispatch_dict = dict()
        for k in dir(r):
            if k.startswith("_report_event_"):
                # have a a handler, wire it up
                dispatch_dict[k[len("_report_event_"):]]=getattr(r,k)

        r.dispatch_dict = dispatch_dict

        return r



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
        return self.accumulated_time

class ThreadLocalTimer(threading_local,Timer):
    pass

class TimerMixin(AutoDispatch,TypedObject):

    timer = ThreadLocalTimer

    def _report_event_start(self,name,param):
        if not self.timer:
            self.timer = ThreadLocalTimer()
            
        self.timer.start()

    def _report_event_end(self,name,param):
        self._report_event(name,"value",self.timer.stop())




class TriggerMixin(AutoDispatch):

    def _report_event_end(self,name,param):
        self._report_event(name,"value",1L)


class EventCounter(TriggerMixin,BaseCounter):

    value = long



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

    values = MemberTypeInfo(type=deque,nullable=False)
    times = MemberTypeInfo(type=deque,nullable=False)
    window_size = float

    def __init__(self,name,window_size=300.0,output_log=None,parent=None):
        super(AverageWindowCounter,self).__init__(name,output_log=output_log,parent=parent)
        self.window_size=window_size


    def _clear(self):
        self.values.clear()
        self.times.clear()

    def _get_value(self):
        self._trim_window()
        if not self.values:
            return 0.0
        return sum(self.values, 0.0) / len(self.values)

    def _trim_window(self):
        window_limit = time()-self.window_size
        # trim old data
        while self.times and self.times[0] < window_limit:
            self.times.popleft()
            self.values.popleft()


    def _report_event_value(self,param,value):
        self._trim_window()
        self.values.append(value)
        self.times.append(time())

class FrequencyCounter(TriggerMixin,AverageWindowCounter):

    def _get_value(self):
        self._trim_window()
        if not self.values or len(self.values)<2:
            return 0.0
        return sum(self.values, 0.0) / (time()-self.times[0])



class AverageTimeCounter(TimerMixin,AverageWindowCounter):
    
    pass



class ValueAccumulator(AutoDispatch,BaseCounter):
    """ Captures all named values it gets and accumulates them. Also allows rethrowing them, prefixed with their name."""

    accumulated_values = NonNullable(dict)

    # forces the object not to accumulate values. Used when the object itself is raising events
    _ignore_values = MemberTypeInfo(type=bool,default=False)


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



class ThreadTimeCategorizer(TypedObject,BaseListener):
    """ A class to divide the time spent by thread across multiple categories. Categories are mutually exclusive. """

    name = basestring
    category_timers = NonNullable(dict)

    _timer_class = Timer

    def __init__(self,name):
        super(ThreadTimeCategorizer,self).__init__()
        self.name = name

    def report_event(self,name,property,param):
        if property == "start":
            cat_timer = self.category_timers.get(name)
            if not cat_timer:
                cat_timer = self._timer_class()
                self.category_timers[name]=cat_timer

            cat_timer.start()

        elif property == "end":
            cat_timer = self.category_timers[name] # if all went well it is there...
            cat_timer.pause()


   
    def raise_value_events(self,clear=False):
        """ raises category total time as value events. """
        for k,v in self.category_timers.iteritems():
            THREAD_DISPATCHER.disptach_event(self.name + "." + k,"value",v.get_accumulated_time())

        if clear:
            self.category_timers.clear()

