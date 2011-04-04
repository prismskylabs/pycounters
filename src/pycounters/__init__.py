"""

  - cascading reports:
     - global
     - per request
     - types of analyzer needs to be different


  - cascading events:
    - name
    - value (#)



 - Counter
    - Average
        - running window:
            - keeps all info of the last X minutes
        - how to do daily report (start stupid)
            small numbers - better accumulate before
           - sum += x
           - num +=
             idea - work in chunks of 10
                - average is sigma(s,1,n)/n = (sigma(s,1.n/2)/(n/2)+sigma(s,n/2,n)/(n/2))/2

    - Event counter
        - counts the number of time an event has fired

    - GetTimer()
       - returns a timer which fires events to this object
       - timers have name + start + stop
       - events fired are the  difference between start + stop
    - GetSimpleTrigger()
       - returns a counter, firing evens based on name. Value is always one.

    - GetChildProfiler (?)


 - EventTrigger
    - reportsEvent(value) - reports events to the associated  Counter (global or thread specific.
    - is attached to a profiler


 - Counter chaining (later):
        - by name upon registration
            - bla.foo counter forwards its event to boo

        - by thread to global
            - resolving bla.foo, will first get a local counter, then a global one
            - any of them will connect

how to use:
- define output by defining Counter
    - per name, a type.
    - global or per thread.
    - can clean up.


output code (global)
- new Counter(log,output resolution etc.)
- register(Counter)
- unregister(Counter)


output per request (global)
- new Counter(log,counter settings...)
- register_thread(Counter)
- unregister_thread(counter=Counter,name=Name)
_ clean_thread_registery()

@time_function("name") # creates a timer event attached to profiler named name
function(bla)




"""
from functools import wraps
from time import time
from PerfCounters.counters import EventCounter, AverageWindowCounter
from .base import perf_registry


def perf_report_value(name,value,auto_add_counter=AverageWindowCounter):
    cntr=perf_registry.get_counter(name,throw=False)
    if not cntr and auto_add_counter:
        perf_registry.add_counter(auto_add_counter(name))
        cntr=perf_registry.get_counter(name)
    if cntr:
        cntr.report_value(value)


def perf_count(name,auto_add_counter=EventCounter):

    def decorator(f):
        @wraps(f)
        def wrapper(*args,**kwargs):
            perf_report_value(name,1L,auto_add_counter=auto_add_counter)
            return f(*args,**kwargs)

        return wrapper
    return decorator

def perf_time(name,auto_add_counter=AverageWindowCounter):
    def decorator(f):
        @wraps(f)
        def wrapper(*args,**kwargs):
            cntr=perf_registry.get_counter(name,throw=False)
            if not cntr and auto_add_counter:
                perf_registry.add_counter(auto_add_counter(name))
                cntr=perf_registry.get_counter(name)
            st= None
            if cntr:
                st = time()
            r=f(*args,**kwargs)
            if cntr:
                cntr.report_value(time()-st)
            return r

        return wrapper
    return decorator


def perf_register(counter):
    perf_registry.add_counter(counter)


def perf_unregister(counter=None,name=None):
    perf_registry.remove_counter(counter=counter,name=name)