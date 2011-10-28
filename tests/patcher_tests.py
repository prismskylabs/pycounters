from django.test import TestCase
from . import EventCatcher
from pycounters.utils import patcher

__author__ = 'boaz'

CLASS_TO_PATCH = None # used by tests that need a globally findable object

class PatcherTests(TestCase):
    def test_patching_dedup(self):
        class A(object):
            def f(self):
                pass;

        patcher.add_start_end_reporting("event1",A,"f")
        patcher.add_start_end_reporting("event2",A,"f")
        patcher.add_start_end_reporting("event1",A,"f")

        self.assertEqual(patcher._get_existing_wrapped_events(A.f), ["event1","event2"])

    def test_patching_event_firing(self):
        class A(object):
            def f(self):
                pass;

        patcher.add_start_end_reporting("event1",A,"f")
        patcher.add_start_end_reporting("event2",A,"f")

        events=[]
        with EventCatcher(events):
            a= A()
            a.f()

        self.assertEqual(events,
                [
                    ("event2","start",None),
                    ("event1","start",None),
                    ("event1","end",None),
                    ("event2","end",None),
                ]
            )

    def test_patching_scheme(self):
        class A(object):
            def f(self):
                pass;

        global CLASS_TO_PATCH
        CLASS_TO_PATCH = A

        patcher.execute_patching_scheme(
            [ {"class":__name__+".CLASS_TO_PATCH","method":"f","event":"event1"}]
        )


        events=[]
        with EventCatcher(events):
            a= A()
            a.f()

        self.assertEqual(events,
            [
                ("event1","start",None),
                ("event1","end",None),
            ]
        )

        CLASS_TO_PATCH=None
