from pycounters import perf_register, perf_count, perf_unregister, perf_time, perf_frequency
from pycounters.base import CounterRegistry
from pycounters.counters import EventCounter, AverageWindowCounter, AverageTimeCounter, FrequencyCounter
from pycounters.reporters import BaseReporter
import time

__author__ = 'boaz'

import unittest


class MyTestCase(unittest.TestCase):

    def test_perf_time(self):
        c = AverageTimeCounter("c")
        perf_register(c)
        try:
            @perf_time("c")
            def f():
                time.sleep(0.5)

            f()

            self.assertAlmostEqual(c.get_value(),0.5,places=3)
        finally:
            perf_unregister(counter=c)

    def test_perf_frequency(self):
        c = FrequencyCounter("c")
        perf_register(c)
        try:
            @perf_frequency("c")
            def f():
                time.sleep(0.5)

            @perf_frequency("c")
            def g():
                pass

            g()
            f()

            self.assertAlmostEqual(c.get_value(),3.98,places=1)
        finally:
            perf_unregister(counter=c)
        


    def test_average_window_counter(self):
        test = AverageWindowCounter("test",window_size=0.5)
        test.report_value(1)
        test.report_value(2)
        self.assertEquals(test.get_value(),1.5)

        time.sleep(0.5)
        self.assertEquals(test.get_value(),0.0)

        test.report_value(1)
        self.assertEquals(test.get_value(),1.0)




    def test_basic_reporter(self):
        class ValueReporter(BaseReporter):

            def output_report(self,values):
                self.last_values = values

        v = ValueReporter()
        v.start_auto_report(0.05)

        test1= EventCounter("test1")
        perf_register(test1)

        test1.report_value(2)

        time.sleep(0.1)
        self.assertEqual(v.last_values, { "test1" : 2 })

        test1.report_value(1)
        time.sleep(0.1)
        self.assertEqual(v.last_values, { "test1" : 3 })

        v.stop_auto_report()
        test1.report_value(1)
        time.sleep(0.1)
        self.assertEqual(v.last_values, { "test1" : 3 })



    def test_registry_get_values(self):
        reg = CounterRegistry()
        test1= EventCounter("test1")
        reg.add_counter(test1)
        test2=EventCounter("test2")
        reg.add_counter(test2)

        test1.report_value(2)

        test2.report_value(3)

        self.assertEquals(reg.get_values(), { "test1" : 2, "test2" : 3 })





    def test_counted_func(self):
        c = EventCounter("c")
        perf_register(c)

        @perf_count("c")
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

        perf_unregister(counter=c)


    def test_registry_percolation(self):
        rep1 = CounterRegistry()

        rep2 = CounterRegistry(parent=rep1)

        rep1.add_counter(EventCounter("test"))

        c = rep2.get_counter("test",throw=False)
        self.assertTrue(c)


if __name__ == '__main__':
    unittest.main()
