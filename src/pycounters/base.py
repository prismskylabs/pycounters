import logging
from threading import RLock, local as thread_local


class CounterRegistry(object):

    def __init__(self):
        super(CounterRegistry,self).__init__()
        self.lock =RLock()
        self.registry=dict()


    def get_values(self):
        values = dict()
        with self.lock:
            for name,c in self.registry.iteritems():
                values[name]=c.get_value()

        return values


    def add_counter(self,counter,throw=True):
        with self.lock:
            if counter.name in self.registry:
                if throw:
                    raise Exception("A counter named %s is already defined" % (counter.name))
                return False

            self.registry[counter.name] = counter
            return True


    def remove_counter(self,counter=None,name=None):
        with self.lock:
            if counter:
                name=counter.name

            if not name:
                raise Exception("trying to remove a counter from perfomance registry but no counter or name supplied.")

            self.registry.pop(name)

    def get_counter(self,name,throw=True):

        with self.lock:
            c = self.registry.get(name)

            if not c and throw:
                raise Exception("No counter named '%s' found " % (name,) )

            return c


class BaseListener(object):

    def report_event(self,name,property,param):
        """ reports an event to this listener """
        raise NotImplementedError("report_event is not implemented")

class EventLogger(BaseListener):

    def __init__(self,logger,logging_level=logging.DEBUG):
        self.logger = logger
        self.logging_level = logging_level


    def report_event(self,name,property,param):
        self.logger.log(self.logging_level,"Event: name=%s property=%s param=%s",name,property,param)


class RegistryListener(BaseListener):

    def __init__(self,registry):
        """ Registry = CounterRegistry to dispatch events to """
        self.registry=registry


    def report_event(self,name,property,param):
        c = self.registry.get_counter(name,throw=False)
        if c:
            c.report_event(name,property,param)

class EventDispatcher(object):

    def __init__(self):
        self.listeners=set()
        self.lock=RLock()


    def dispatch_event(self,name,property,param):
        with self.lock:
            for l in self.listeners:
                l.report_event(name,property,param)

    def add_listener(self,listener):
        with self.lock:
            self.listeners.add(listener)

    def remove_listener(self,listener):
        with self.lock:
            self.listeners.remove(listener)




class ThreadSpecificDispatcher(thread_local):
    """ A dispatcher handle thread specific dispatching. Also percolates to Global event"""
    ## TODO: work in progress. no clean solution yet.

    def _get_listner_set(self):
        if not hasattr(self,"listeners"):
            self.listeners = set() # new thread

        return self.listeners

    def add_listener(self,listener):
        self._get_listner_set().add(listener)

    def remove_listener(self,listener):
        self._get_listner_set().remove(listener)


    def disptach_event(self,name,property,param):
        # first event specific
        ls = self._get_listner_set()
        if ls:
            for l in ls:
                l.report_event(name,property,param)

        # finally dispatch it globally..
        global GLOBAL_DISPATCHER
        GLOBAL_DISPATCHER.dispatch_event(name,property,param)






GLOBAL_REGISTRY = CounterRegistry()

GLOBAL_DISPATCHER = EventDispatcher()
GLOBAL_DISPATCHER.add_listener(RegistryListener(GLOBAL_REGISTRY))

THREAD_DISPATCHER = ThreadSpecificDispatcher()