from collections import deque
from threading import RLock, local as threading_local
from time import time
from typeinfo import MemberTypeInfo, TypedObject

__author__ = 'boaz'


class BaseCounter(TypedObject):

    name = MemberTypeInfo(type=basestring,nullable=False,none_on_init=True)

    lock = MemberTypeInfo(type=RLock().__class__,nullable=False) # RLock hides the actual class.


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



class ThreadTimer(threading_local):
    """ a thread specific timer. """

    def _get_current_time(self):
        return time()

    def start(self):
        """ start timing """
        self.start_time = self._get_current_time()
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


class TimerMixin(AutoDispatch,TypedObject):

    timer = ThreadTimer

    def _report_event_start(self,name,param):
        if not self.timer:
            self.timer = ThreadTimer()
            
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