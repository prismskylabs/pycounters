from threading import RLock
from typeinfo import TypedObject, MemberTypeInfo



class CounterRegistry(TypedObject):

    lock = MemberTypeInfo(type=RLock().__class__,nullable=False) # RLock hides the actual class.

    registry = MemberTypeInfo(type=dict,nullable=False)

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




GLOBAL_REGISTRY = CounterRegistry()

perf_registry = GLOBAL_REGISTRY
