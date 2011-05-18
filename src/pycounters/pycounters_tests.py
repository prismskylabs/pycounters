from pycounters import register_counter, count, perf_unregister, perf_time, frequency
from pycounters.base import CounterRegistry
from pycounters.counters import EventCounter, AverageWindowCounter, AverageTimeCounter, FrequencyCounter, ThreadTimer
from pycounters.reporters import BaseReporter
import time

__author__ = 'boaz'

import unittest


class FakeTimer(ThreadTimer):
    """ causes time to behave rationaly so it can be tested. """

    def _get_current_time(self):
        if hasattr(self,"curtime"):
            self.curtime +=1
        else:
            self.curtime = 0
        return self.curtime

class MyTestCase(unittest.TestCase):

    def test_Thread_Timer(self):
        f = FakeTimer()
        f.start()
        self.assertEqual(f.stop(),1)
        f.start()
        self.assertEqual(f.pause(),1)
        f.start()
        self.assertEqual(f.stop(),2)


    def test_perf_time(self):
        c = AverageTimeCounter("c")
        c.timer = FakeTimer()
        register_counter(c)
        try:
            @perf_time("c")
            def f():
                c.timer._get_current_time() # advances time -> just like sleep 1
                pass

            f()
            f()

            self.assertEqual(c.get_value(),2)
        finally:
            perf_unregister(counter=c)

    def test_perf_frequency(self):
        c = FrequencyCounter("c")
        register_counter(c)
        try:
            @frequency("c")
            def f():
                time.sleep(0.5)

            @frequency("c")
            def g():
                pass

            g()
            f()

            self.assertAlmostEqual(c.get_value(),3.98,places=1)
        finally:
            perf_unregister(counter=c)
        


    def test_average_window_counter(self):
        test = AverageWindowCounter("test",window_size=0.5)
        test.report_event("test","value",1)
        test.report_event("test","value",2)
        self.assertEquals(test.get_value(),1.5)

        time.sleep(0.5)
        self.assertEquals(test.get_value(),0.0)

        test.report_event("test","value",1)
        self.assertEquals(test.get_value(),1.0)




    def test_basic_reporter(self):
        class ValueReporter(BaseReporter):

            def output_report(self,values):
                self.last_values = values

        v = ValueReporter()
        v.start_auto_report(0.05)

        test1= EventCounter("test1")
        register_counter(test1)

        test1.report_event("test1","value",2)

        time.sleep(0.1)
        self.assertEqual(v.last_values, { "test1" : 2 })

        test1.report_event("test1","value",1)
        time.sleep(0.1)
        self.assertEqual(v.last_values, { "test1" : 3 })

        v.stop_auto_report()
        test1.report_event("test1","value",1)
        time.sleep(0.1)
        self.assertEqual(v.last_values, { "test1" : 3 })



    def test_registry_get_values(self):
        reg = CounterRegistry()
        test1= EventCounter("test1")
        reg.add_counter(test1)
        test2=EventCounter("test2")
        reg.add_counter(test2)

        test1.report_event("test1","value",2)

        test2.report_event("test1","value",3)

        self.assertEquals(reg.get_values(), { "test1" : 2, "test2" : 3 })





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

            self.assertEqual(c.get_value(),3L)

            c.clear()

            self.assertEqual(c.get_value(),0L)

            f()

            self.assertEqual(c.get_value(),1L)
        finally:
            perf_unregister(counter=c)


    def test_registry_percolation(self):
        rep1 = CounterRegistry()

        rep2 = CounterRegistry(parent=rep1)

        rep1.add_counter(EventCounter("test"))

        c = rep2.get_counter("test",throw=False)
        self.assertTrue(c)


if __name__ == '__main__':
    unittest.main()
