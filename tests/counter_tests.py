import os
import unittest
from time import sleep

from pycounters import register_counter, report_start_end, unregister_counter, register_reporter, start_auto_reporting, unregister_reporter, stop_auto_reporting, report_value
from pycounters.base import CounterRegistry, THREAD_DISPATCHER, EventDispatcher
from pycounters.counters import EventCounter, AverageWindowCounter, AverageTimeCounter, FrequencyCounter, ValueAccumulator, ThreadTimeCategorizer, TotalCounter
from pycounters.counters.base import BaseCounter, Timer, ThreadLocalTimer, AverageCounterValue, AccumulativeCounterValue, MinCounterValue, MaxCounterValue
from pycounters.reporters import JSONFileReporter
from pycounters.reporters.base import BaseReporter, GLOBAL_REPORTING_CONTROLLER
from pycounters.shortcuts import count, value, frequency, time
from . import EventCatcher


class FakeThreadLocalTimer(ThreadLocalTimer):
    """ causes time to behave rationaly so it can be tested. """

    def _get_current_time(self):
        if hasattr(self, "curtime"):
            self.curtime += 1
        else:
            self.curtime = 0
        return self.curtime

class SimpleValueReporter(BaseReporter):
    def output_values(self,counter_values):
        self.last_values = counter_values

    @property
    def values_wo_metadata(self):
        return dict([(k,v) for k,v in self.last_values.iteritems() if not k.startswith("__")])

class FakeTimer(Timer):
    """ causes time to behave rationaly so it can be tested. """

    def _get_current_time(self):
        if hasattr(self, "curtime"):
            self.curtime += 1
        else:
            self.curtime = 0
        return self.curtime

class CounterTests(unittest.TestCase):
    def test_ThreadTimeCategorizer(self):
        tc = ThreadTimeCategorizer("tc", ["cat1", "cat2", "f"], timer_class=FakeTimer)
        THREAD_DISPATCHER.add_listener(tc)

        try:
            @report_start_end("cat1")
            def cat1():
                pass

            @report_start_end("cat2")
            def cat2():
                pass

            @report_start_end()
            def multicat():
                cat1()
                cat2()

            def f():
                with report_start_end("f"):
                    multicat()
                    cat1()

            f()

            events = []
            with EventCatcher(events):
                tc.raise_value_events()

            self.assertEqual(events,
                [
                    ("tc.cat1", "value", 2.0),
                    ("tc.cat2", "value", 1.0),
                    ("tc.f", "value", 4.0),
                ]
            )

        finally:
            THREAD_DISPATCHER.remove_listener(tc)

    def test_ValueAccumulator(self):

        events = []
        with EventCatcher(events):
            ac = ValueAccumulator(name="ac")
            THREAD_DISPATCHER.add_listener(ac)

            try:
                value("s1", 1, auto_add_counter=False)
                value("s1", 2, auto_add_counter=False)
                value("s2", 5, auto_add_counter=False)

                ac.raise_value_events()

            finally:
                THREAD_DISPATCHER.remove_listener(ac)

        self.assertEqual(events,
                [
                    ("s1", "value", 1),
                    ("s1", "value", 2),
                    ("s2", "value", 5),
                    ("ac.s2", "value", 5),
                    ("ac.s1", "value", 3),
                ]
            )

    def test_report_start_end(self):

        events = []
        with EventCatcher(events):
            @report_start_end()
            def f():
                pass

            f()


            @report_start_end("h")
            def g():
                pass

            g()


            def raises():
                with report_start_end():pass


            self.assertRaises(Exception,raises)

        self.assertEqual(events,
                [
                    ("f", "start", None),
                    ("f", "end", None),
                    ("h", "start", None),
                    ("h", "end", None),
                ]
            )



    def test_Thread_Timer(self):
        f = FakeThreadLocalTimer()
        f.start()
        self.assertEqual(f.stop(), 1)
        f.start()
        self.assertEqual(f.pause(), 1)
        f.start()
        self.assertEqual(f.stop(), 2)


    def test_one_counter_multiple_events(self):
        test = TotalCounter("test",events=["test1","test2"])
        register_counter(test)

        test.report_event("test1", "value", 1)
        test.report_event("test2", "value", 2)
        self.assertEquals(test.get_value().value, 3)

        unregister_counter(counter=test)

    def test_multiple_counters_one_event(self):
        test1 = TotalCounter("test1",events=["test"])
        register_counter(test1)
        test2 = TotalCounter("test2",events=["test"])
        register_counter(test2)

        v = SimpleValueReporter()
        register_reporter(v)

        report_value("test",1)
        GLOBAL_REPORTING_CONTROLLER.report()
        self.assertEquals(v.values_wo_metadata,dict(test1=1,test2=1))

        unregister_counter(counter=test1)
        unregister_counter(counter=test2)

        unregister_reporter(reporter=v)




    def test_perf_time(self):
        c = AverageTimeCounter("c")
        c.timer = FakeThreadLocalTimer()
        register_counter(c)
        try:
            @time(name="c")
            def f():
                c.timer._get_current_time() # advances time -> just like sleep 1
                pass

            f()
            f()

            self.assertEqual(c.get_value().value, 2)
        finally:
            unregister_counter(counter=c)

    def test_perf_frequency(self):
        class FakeFrequencyCounter(FrequencyCounter):

            i = 0

            def _get_current_time(self):
                self.i = self.i + 1
                return self.i

        c = FakeFrequencyCounter("c",events=["f","c"], window_size=10)
        register_counter(c)
        try:
            @frequency()
            def f():
                pass

            @frequency("c")
            def g():
                pass

            f()
            g()

            self.assertEquals(c.get_value().value, 0.5)
        finally:
            unregister_counter(counter=c)

    def test_average_window_counter(self):
        test = AverageWindowCounter("test", window_size=0.5)
        test.report_event("test", "value", 1)
        test.report_event("test", "value", 2)
        self.assertEquals(test.get_value().value, 1.5)

        sleep(0.7)
        self.assertEquals(test.get_value().value, None)

        test.report_event("test", "value", 1)
        self.assertEquals(test.get_value().value, 1.0)

    def test_total_counter(self):
        test = TotalCounter("test")
        self.assertEquals(test.get_value().value, None)
        test.report_event("test", "value", 1)
        test.report_event("test", "value", 2)
        self.assertEquals(test.get_value().value, 3)

        test.clear(dump=False)
        test.report_event("test", "value", 1)
        self.assertEquals(test.get_value().value, 1)

    def test_basic_reporter(self):

        test1 = EventCounter("test1")
        register_counter(test1)

        v = SimpleValueReporter()
        register_reporter(v)
        start_auto_reporting(0.01)


        try:
            test1.report_event("test1", "value", 2)

            sleep(0.1)
            self.assertEqual(v.values_wo_metadata, {"test1": 2})

            test1.report_event("test1", "value", 1)
            sleep(0.05)
            self.assertEqual(v.values_wo_metadata, {"test1": 3})

            stop_auto_reporting()
            test1.report_event("test1", "value", 1)
            sleep(0.05)
            self.assertEqual(v.values_wo_metadata, {"test1": 3})
        finally:
            unregister_counter(counter=test1)
            unregister_reporter(v)

    def test_registry_get_values(self):
        reg = CounterRegistry(EventDispatcher())
        test1 = EventCounter("test1")
        reg.add_counter(test1)
        test2 = EventCounter("test2")
        reg.add_counter(test2)

        test1.report_event("test1", "value", 2)

        test2.report_event("test1", "value", 3)

        self.assertEquals(reg.get_values().values, {"test1": 2, "test2": 3})

    def test_counted_func(self):
        c = EventCounter("c")
        register_counter(c)

        try:
            @count("c")
            def f():
                pass

            f()
            f()
            f()

            self.assertEqual(c.get_value().value, 3L)

            c.clear()

            self.assertEqual(c.get_value().value, 0L)

            f()

            self.assertEqual(c.get_value().value, 1L)
        finally:
            unregister_counter(counter=c)

    def test_average_counter_value(self):
        a = AverageCounterValue(1,1)
        b = AverageCounterValue(3,3)
        a.merge_with(b)
        b = AverageCounterValue(None,0)
        a.merge_with(b)
        self.assertEquals(a.value, 2.5)

    def test_accumulative_counter_value(self):
        a = AccumulativeCounterValue(1)
        b = AccumulativeCounterValue(3)
        a.merge_with(b)
        b = AccumulativeCounterValue(None)
        a.merge_with(b)
        self.assertEquals(a.value, 4)

    def test_min_counter_value(self):
        a = MinCounterValue(1)
        b = MinCounterValue(3)
        a.merge_with(b)
        self.assertEquals(a.value, 1)
        c = MinCounterValue(0)
        a.merge_with(c)
        self.assertEquals(a.value, 0)
        b.value = None
        a.merge_with(b)
        self.assertEquals(a.value, 0)

    def test_max_counter_value(self):
        a = MaxCounterValue(3)
        b = MaxCounterValue(1)
        a.merge_with(b)
        self.assertEquals(a.value, 3)
        c = MaxCounterValue(4)
        a.merge_with(c)
        self.assertEquals(a.value, 4)
        b.value = None
        a.merge_with(b)
        self.assertEquals(a.value, 4)




    def test_json_output(self):
        filename = "/tmp/json_test.txt"
        jsfr = JSONFileReporter(output_file=filename)
        test1 = EventCounter("test1")
        register_counter(test1)
        register_reporter(jsfr)

        try:
            test1.report_event("test1", "value", 2)

            GLOBAL_REPORTING_CONTROLLER.report()
            report = JSONFileReporter.safe_read(filename)
            report = dict([(k,v) for k,v in report.iteritems() if not k.startswith("__")])
            self.assertEqual(report, {"test1": 2})

            os.unlink(filename)
        finally:
            unregister_counter(counter=test1)
            unregister_reporter(jsfr)
