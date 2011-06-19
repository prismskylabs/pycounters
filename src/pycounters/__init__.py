"""

PyCounters is a light weight library to monitor performance in production system.
It is meant to be used in scenarios where using a profile is unrealistic due to the overhead it requires.
Use PyCounters to get high level and concise overview of what's going on in your production code.

See #### (read the docs) for more information

"""
import base
from shortcuts import _make_reporting_decorator


def report_start(name):
    """ reports an event's start.
        NOTE: you *must*  fire off a corresponding event end with report_end
    """
    base.THREAD_DISPATCHER.disptach_event(name,"start",None)

def report_end(name):
    """ reports an event's end.
        NOTE: you *must* have fired off a corresponding event end with report_start
    """
    base.THREAD_DISPATCHER.disptach_event(name,"end",None)

def report_start_end(name):
    """
     returns a function decorator which raises start and end events
    """
    return _make_reporting_decorator(name)


def report_value(name,value):
    """
     reports a value event to the counters.
    """

    base.THREAD_DISPATCHER.disptach_event(name,"value",value)

def register_counter(counter,throw_if_exists=True):
    """ Register a counter with PyCounters
    """
    base.GLOBAL_REGISTRY.add_counter(counter,throw=throw_if_exists)


def unregister_counter(counter=None,name=None):
    """ Removes a previously registered counter
    """
    base.GLOBAL_REGISTRY.remove_counter(counter=counter,name=name)