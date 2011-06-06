"""

PyCounters is a light weight library to monitor performance in production system.
It is meant to be used in scenarios where using a profile is unrealistic due to the overhead it requires.
Use PyCounters to get high level and concise overview of what's going on in your production code.

See #### (read the docs) for more information

"""
from functools import wraps
import base
import counters

def _make_reporting_decorator(name,auto_add_counter=None):
    def decorator(f):
        @wraps(f)
        def wrapper(*args,**kwargs):
            if auto_add_counter:
                cntr=base.GLOBAL_REGISTRY.get_counter(name,throw=False)
                if not cntr:
                    base.GLOBAL_REGISTRY.add_counter(auto_add_counter(name),throw=True)

            base.THREAD_DISPATCHER.disptach_event(name,"start",None)
            try:
                r=f(*args,**kwargs)
            finally:
                ## make sure calls are balanced
                base.THREAD_DISPATCHER.disptach_event(name,"end",None)
            return r

        return wrapper
    return decorator


def report_start(name):
    """ reports an event's start.
        NOTE: you *must*  fire off a corresponding event end with report_end
    """
    base.THREAD_DISPATCHER.disptach_event(name,"start",None)

def report_end(name):
    """ reports an event's end.
        NOTE: you *must* have fire doff a corresponding event end with report_start
    """
    base.THREAD_DISPATCHER.disptach_event(name,"end",None)

def report_start_end(name):
    """
     returns a function decorator which raises start and end events
    """
    return _make_reporting_decorator(name)


def report_value(name,value):

    base.THREAD_DISPATCHER.disptach_event(name,"value",value)

def occurrence(name,auto_add_counter=counters.FrequencyCounter):
    """
      A shortcut function reports an occurrence of something. Uses the :obj:`counters.FrequencyCounter` counter by default.
    """
    if auto_add_counter:
        cntr= base.GLOBAL_REGISTRY.get_counter(name,throw=False)
        if not cntr:
            base.GLOBAL_REGISTRY.add_counter(auto_add_counter(name),throw=False)

    base.THREAD_DISPATCHER.disptach_event(name,"end",None)



def count(name,auto_add_counter=counters.EventCounter):
    """
        A shortcut decorator to count the number times a function is run. Uses the :obj:`counters.EventCounter` counter by default.
    """
    return _make_reporting_decorator(name,auto_add_counter=auto_add_counter)

def frequency(name,auto_add_counter=counters.FrequencyCounter):
    """
        A shortcut decorator to count the frequency in which a function is called. Uses the :obj:`counters.FrequencyCounter` counter by default.
    """
    return _make_reporting_decorator(name,auto_add_counter=auto_add_counter)


def time(name,auto_add_counter=counters.AverageTimeCounter):
    """
        A shortcut decorator to count the average execution time of a function. Uses the :obj:`counters.AverageTimeCounter` counter by default.
    """
    return _make_reporting_decorator(name,auto_add_counter=auto_add_counter)


def value(name,value,auto_add_counter=counters.AverageWindowCounter):
    """
      A shortcut function reports an value of something. Uses the :obj:`counters.AverageWindowCounter` counter by default.
    """
    if auto_add_counter:
        cntr= base.GLOBAL_REGISTRY.get_counter(name,throw=False)
        if not cntr:
            base.GLOBAL_REGISTRY.add_counter(auto_add_counter(name),throw=False)

    base.THREAD_DISPATCHER.disptach_event(name,"value",value)



def register_counter(counter,throw_if_exists=True):
    """ Register a counter with PyCounters
    """
    base.GLOBAL_REGISTRY.add_counter(counter,throw=throw_if_exists)


def unregister_counter(counter=None,name=None):
    """ Removes a previously registered counter
    """
    base.GLOBAL_REGISTRY.remove_counter(counter=counter,name=name)