from pycounters.base import THREAD_DISPATCHER, BaseListener



class EventCatcher(object):

    def __init__(self,event_store):
        self.event_store = event_store

    def create_listener(self,event_store):
        class listener(BaseListener):

            def _report_event(self, name, property, param):
                event_store.event_store.append((name, property, param))

        return listener()



    def __enter__(self):
        self.event_trace = self.create_listener(self.event_store)
        THREAD_DISPATCHER.add_listener(self.event_trace)

    def __exit__(self,*args):
        THREAD_DISPATCHER.remove_listener(self.event_trace)
