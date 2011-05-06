from collections import deque
from threading import RLock
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

    def report_value(self,value):
        """ reports a value to this counter """
        if self.parent: self.parent.report_event(value)
        with self.lock:
            self._report_event(value)

    def get_value(self):
        with self.lock:
            return self._get_value()

    def clear(self,dump=True):
        with self.lock:
            if dump and self.output_log:
                self.output_log.info("Counter '%': %s",self.name,self.get_value())
            self._clear()

    def _report_event(self,value):
        """ implement this in sub classes """
        raise NotImplementedError("_report_event is not implemented")

    def _get_value(self):
        """ implement this in sub classes """
        raise NotImplementedError("_get_value is not implemented")

    def _clear(self):
        """ implement this in sub classes """
        raise NotImplementedError("_clear is not implemented")


class StartEndMixinBase(TypedObject):

    def report_event_start(self):
        pass

    def report_event_end(self,event_start_return):
        pass



class TriggerMixin(StartEndMixinBase):

    def report_event_start(self):
        pass

    def report_event_end(self,event_start_return):
        self.report_value(1L)

class TimerMixin(StartEndMixinBase):

    def report_event_start(self):
        return time()

    def report_event_end(self,event_start_return):
        self.report_value(time()-event_start_return)




class EventCounter(TriggerMixin,BaseCounter):

    value = long



    def _get_value(self):
        return self.value;

    def _report_event(self,value):

        if self.value:
            self.value += value
        else:
            self.value = long(value)


    def _clear(self):
        self.value = 0L


class AverageWindowCounter(BaseCounter):

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


    def _report_event(self,value):
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