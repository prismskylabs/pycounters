from threading import RLock, local as thread_local
from typeinfo import TypedObject, NonNullable


class CounterRegistry(TypedObject):

    lock = NonNullable(RLock().__class__) # RLock hides the actual class.

    registry = NonNullable(dict)

    def __init__(self,parent=None):
        super(CounterRegistry,self).__init__()
        self.parent=parent # used to percolate changes from local thread to parent thread


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
            if self.parent:
                c = self.parent.get_counter(counter.name)
                if c:
                    counter.parent =c
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
            if not c and self.parent:
                c = self.parent.get_counter(name,throw=False)

            if not c and throw:
                raise Exception("No counter named '%s' found " % (name,) )

            return c



class EventDispatcher(TypedObject):
    registry = NonNullable(CounterRegistry)

    def __init__(self,registry):
        """ Registry = CounterRegistry to dispatch events to """
        self.registry=registry


    def dispatch_event(self,name,property,param):
        c = self.registry.get_counter(name,throw=False)
        if c:
            c.report_event(name,property,param)



class ThreadSpecificDispatcher(TypedObject,thread_local):
    """ A dispatcher handle thread specific dispatching. Also percolates to Global event"""
    ## TODO: work in progress. no clean solution yet.

    listeners = NonNullable(dict) # a dictionary of sets of listeners

    def _get_listner_set(self, event,auto_add=True):
        listener_set = self.listeners.get(event)
        if listener_set is None:
            if auto_add:
                listener_set = set()
                self.listeners[event] = listener_set
                return listener_set
            else:
                return None
        return listener_set

    def add_listener(self,listener,event="*"):
        listener_set = self._get_listner_set(event)
        listener_set.add(listener)

    def remove_listener(self,listener,event="*"):
        listener_set = self._get_listner_set(event)
        listener_set.remove(listener)


    def disptach_event(self,name,property,param):
        # first event specific
        ls = self._get_listner_set(name,auto_add=False)
        if ls:
            for l in ls:
                l.report_event(name,property,param)

        # now listeners for *
        ls = self._get_listner_set("*",auto_add=False)
        if ls:
            for l in ls:
                l.report_event(name,property,param)


        # finally dispatch it globally..
        global GLOBAL_DISPATCHER
        GLOBAL_DISPATCHER.dispatch_event(name,property,param)






GLOBAL_REGISTRY = CounterRegistry()

GLOBAL_DISPATCHER = EventDispatcher(GLOBAL_REGISTRY)

THREAD_DISPATCHER = ThreadSpecificDispatcher()