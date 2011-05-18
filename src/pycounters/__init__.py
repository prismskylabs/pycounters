"""
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

@perf_time("name") # creates a timer event attached to profiler named name
function(bla)


---- Yet again, writing use cases

    - Using default

    - Count how many times a function is called since last output
            @perf_count(name)
            def func()
               pass

            fires off an event + 1 as value
            Counter - EventCounter
            Events - name , value =1


    - Count how what the average value of something in last 5 minutes
            perf_average_value(name,value)

            Counter - AverageCounter
            Event - name + value


    - Measure the frequency a function is executed
            @perf_frequency(name)
            def f():
                pass

            Counter - FrequencyCounter
            Event - name + 1

    - Measure the average time a function executes
            @perf_time(name)
            def f():
                pass

            Counter - AverageTimeCounter
            Event - name:start
                    name:end


    - Django:
        - per view:
            know the total time
            out of which how much was spent on:
                template rendering
                DB access
                Allow for interwind access (while rendering to DB access or what ever
            what ever else is interesting

            @perf_time("bla")
            @perf_thread_timer
            def view()
                some db access
                g()
                render template



            Counters:
                AverageCounters per view per category

Events:
    - Name, property (start,end, value) , param

Dispatcher
    - Global
        - dispatches events based on name to registered counters
        - Counters can register under "*" to get all events.

    - Thread specific
        - Same thing as global but thread specific.

    - Counters can be registered and unregistered.


Counters
    - Time based counters
        - capture start events and park the time on a thread local store
        - capture end events calc time and rethrow value events.

    - TimeAccumulator
        - A special counter that graps start/end events and time the in a mutual exclusive way
        - the start of one event is the end of the previous one. The end of the current one means restarting
            the time running before it.

        - Contains a method to fire value events with the total values so far


    - EventLoggingCounter


Reporters
    - Report reports from dispatchers.
    - May be thread specific

"""
from functools import wraps
from .counters import EventCounter, AverageWindowCounter, AverageTimeCounter, FrequencyCounter
from .base import THREAD_DISPATCHER, GLOBAL_REGISTRY


def _make_reporting_decorator(name,auto_add_counter=None):
    def decorator(f):
        @wraps(f)
        def wrapper(*args,**kwargs):
            cntr=GLOBAL_REGISTRY.get_counter(name,throw=False)
            if not cntr and auto_add_counter:
                perf_registry.add_counter(auto_add_counter(name))
                cntr=perf_registry.get_counter(name)

            THREAD_DISPATCHER.disptach_event(name,"start",None)
            r=f(*args,**kwargs)
            THREAD_DISPATCHER.disptach_event(name,"end",None)
            return r

        return wrapper
    return decorator

def perf_report_value(name,value,auto_add_counter=AverageWindowCounter):
    cntr=GLOBAL_REGISTRY.get_counter(name,throw=False)
    if not cntr and auto_add_counter:
        GLOBAL_REGISTRY.add_counter(auto_add_counter(name),throw=False)

    THREAD_DISPATCHER.disptach_event(name,"value",value)


def perf_count(name,auto_add_counter=EventCounter):
    return _make_reporting_decorator(name,auto_add_counter=auto_add_counter)

def perf_frequency(name,auto_add_counter=FrequencyCounter):
    return _make_reporting_decorator(name,auto_add_counter=auto_add_counter)


def perf_time(name,auto_add_counter=AverageTimeCounter):
    return _make_reporting_decorator(name,auto_add_counter=auto_add_counter)


def perf_register(counter):
    GLOBAL_REGISTRY.add_counter(counter)


def perf_unregister(counter=None,name=None):
    GLOBAL_REGISTRY.remove_counter(counter=counter,name=name)