from functools import wraps
import base
import counters


def count(name=None,auto_add_counter=counters.EventCounter):
    """
        A shortcut decorator to count the number times a function is called. Uses the :obj:`counters.EventCounter` counter by default.
        If the parameter name is not supplied events are reported under the name of the wrapped function.
    """
    return _make_reporting_decorator(name,auto_add_counter=auto_add_counter)


def value(name,value,auto_add_counter=counters.AverageWindowCounter):
    """
      A shortcut function to report a value of something. Uses the :obj:`counters.AverageWindowCounter` counter by default.
    """
    if auto_add_counter:
        cntr= base.GLOBAL_REGISTRY.get_counter(name,throw=False)
        if not cntr:
            base.GLOBAL_REGISTRY.add_counter(auto_add_counter(name),throw=False)

    base.THREAD_DISPATCHER.dispatch_event(name,"value",value)


def occurrence(name,auto_add_counter=counters.FrequencyCounter):
    """
      A shortcut function reports an occurrence of something. Uses the :obj:`counters.FrequencyCounter` counter by default.
    """
    if auto_add_counter:
        cntr= base.GLOBAL_REGISTRY.get_counter(name,throw=False)
        if not cntr:
            base.GLOBAL_REGISTRY.add_counter(auto_add_counter(name),throw=False)

    base.THREAD_DISPATCHER.dispatch_event(name,"end",None)


def frequency(name=None,auto_add_counter=counters.FrequencyCounter):
    """
        A shortcut decorator to count the frequency in which a function is called. Uses the :obj:`counters.FrequencyCounter` counter by default.
        If the parameter name is not supplied events are reported under the name of the wrapped function.
    """
    return _make_reporting_decorator(name,auto_add_counter=auto_add_counter)


def time(name=None,auto_add_counter=counters.AverageTimeCounter):
    """
        A shortcut decorator to count the average execution time of a function. Uses the :obj:`counters.AverageTimeCounter` counter by default.
        If the parameter name is not supplied events are reported under the name of the wrapped function.
    """
    return _make_reporting_decorator(name,auto_add_counter=auto_add_counter)


def _make_reporting_decorator(name,auto_add_counter=None):
    def decorator(f):
        event_name = name if name else f.__name__

        @wraps(f)
        def wrapper(*args,**kwargs):
            if auto_add_counter:
                cntr=base.GLOBAL_REGISTRY.get_counter(event_name,throw=False)
                if not cntr:
                    base.GLOBAL_REGISTRY.add_counter(auto_add_counter(event_name),throw=True)

            base.THREAD_DISPATCHER.dispatch_event(event_name,"start",None)
            try:
                r=f(*args,**kwargs)
            finally:
                ## make sure calls are balanced
                base.THREAD_DISPATCHER.dispatch_event(event_name,"end",None)
            return r

        return wrapper
    return decorator