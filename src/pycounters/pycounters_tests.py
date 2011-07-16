import logging
import multiprocessing
import threading
from time import sleep
from pycounters import register_counter, report_start_end, unregister_counter
from pycounters.base import CounterRegistry, THREAD_DISPATCHER, CounterValueCollection
from pycounters.counters import EventCounter, AverageWindowCounter, AverageTimeCounter, FrequencyCounter, ValueAccumulator, ThreadTimeCategorizer
from pycounters.counters.base import BaseCounter, Timer, ThreadLocalTimer, AverageCounterValue, AccumulativeCounterValue, MinCounterValue, MaxCounterValue
from pycounters.reporters import BaseReporter, MultiprocessReporterBase, ReportingRole
from pycounters.reporters.tcpcollection import CollectingLeader, CollectingNode, elect_leader
from pycounters.shortcuts import count, value, frequency, time

__author__ = 'boaz'

import unittest




class FakeThreadLocalTimer(ThreadLocalTimer):
    """ causes time to behave rationaly so it can be tested. """

    def _get_current_time(self):
        if hasattr(self,"curtime"):
            self.curtime +=1
        else:
            self.curtime = 0
        return self.curtime

class FakeTimer(Timer):
    """ causes time to behave rationaly so it can be tested. """

    def _get_current_time(self):
        if hasattr(self,"curtime"):
            self.curtime +=1
        else:
            self.curtime = 0
        return self.curtime



class EventTrace(BaseCounter):

    def __init__(self,*args,**kwargs):
        self.value = []
        super(EventTrace,self).__init__(*args,**kwargs)

    def _report_event(self,name,property,param):
        self.value.append((name,property,param))


    def _get_value(self):
        return self.value


class MyTestCase(unittest.TestCase):


    def test_ThreadTimeCategorizer(self):
        tc = ThreadTimeCategorizer("tc",["cat1","cat2","f"],timer_class=FakeTimer)
        THREAD_DISPATCHER.add_listener(tc)

        try:
            @report_start_end("cat1")
            def cat1():
                pass

            @report_start_end("cat2")
            def cat2():
                pass

            @report_start_end("multicat")
            def multicat():
                cat1()
                cat2()

            @report_start_end("f")
            def f():
                multicat()
                cat1()

            f()

            c = EventTrace("c")
            THREAD_DISPATCHER.add_listener(c)
            try:
                tc.raise_value_events()
                self.assertEqual(c.get_value(),
                    [
                        ("tc.cat1","value",2.0),
                        ("tc.cat2","value",1.0),
                        ("tc.f","value",4.0),
                    ]
                )
            finally:
                THREAD_DISPATCHER.remove_listener(c)

        finally:
            THREAD_DISPATCHER.remove_listener(tc)
        


    def test_ValueAccumulator(self):
        c = EventTrace("c")
        ac = ValueAccumulator(name="ac")
        THREAD_DISPATCHER.add_listener(ac)
        THREAD_DISPATCHER.add_listener(c)
        try:
            value("s1",1,auto_add_counter=False)
            value("s1",2,auto_add_counter=False)
            value("s2",5,auto_add_counter=False)

            ac.raise_value_events()


            self.assertEqual(c.get_value(),
                [
                    ("s1","value",1),
                    ("s1","value",2),
                    ("s2","value",5),
                    ("ac.s2","value",5),
                    ("ac.s1","value",3),
                ]
            )
        finally:
            THREAD_DISPATCHER.remove_listener(ac)
            THREAD_DISPATCHER.remove_listener(c)



    def test_Thread_Timer(self):
        f = FakeThreadLocalTimer()
        f.start()
        self.assertEqual(f.stop(),1)
        f.start()
        self.assertEqual(f.pause(),1)
        f.start()
        self.assertEqual(f.stop(),2)


    def test_perf_time(self):
        c = AverageTimeCounter("c")
        c.timer = FakeThreadLocalTimer()
        register_counter(c)
        try:
            @time("c")
            def f():
                c.timer._get_current_time() # advances time -> just like sleep 1
                pass

            f()
            f()

            self.assertEqual(c.get_value().value,2)
        finally:
            unregister_counter(counter=c)

    def test_perf_frequency(self):
        class FakeFrequencyCounter(FrequencyCounter):

            i = 0

            def _get_current_time(self):
                self.i = self.i+1
                return self.i

        c = FakeFrequencyCounter("c",window_size=10)
        register_counter(c)
        try:
            @frequency("c")
            def f():
                pass

            @frequency("c")
            def g():
                pass

            g()
            f()

            self.assertEquals(c.get_value().value,0.5)
        finally:
            unregister_counter(counter=c)
        


    def test_average_window_counter(self):
        test = AverageWindowCounter("test",window_size=0.5)
        test.report_event("test","value",1)
        test.report_event("test","value",2)
        self.assertEquals(test.get_value().value,1.5)

        sleep(0.5)
        self.assertEquals(test.get_value().value,0.0)

        test.report_event("test","value",1)
        self.assertEquals(test.get_value().value,1.0)




    def test_basic_reporter(self):
        class ValueReporter(BaseReporter):

            def _output_report(self,counter_values_col):
                self.last_values = counter_values_col.values


        v = ValueReporter()
        v.start_auto_report(0.01)

        test1= EventCounter("test1")
        register_counter(test1)

        test1.report_event("test1","value",2)

        sleep(0.1)
        self.assertEqual(v.last_values, { "test1" : 2 })

        test1.report_event("test1","value",1)
        sleep(0.05)
        self.assertEqual(v.last_values, { "test1" : 3 })

        v.stop_auto_report()
        test1.report_event("test1","value",1)
        sleep(0.05)
        self.assertEqual(v.last_values, { "test1" : 3 })



    def test_registry_get_values(self):
        reg = CounterRegistry()
        test1= EventCounter("test1")
        reg.add_counter(test1)
        test2=EventCounter("test2")
        reg.add_counter(test2)

        test1.report_event("test1","value",2)

        test2.report_event("test1","value",3)

        self.assertEquals(reg.get_values().values, { "test1" : 2, "test2" : 3 })





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

            self.assertEqual(c.get_value().value,3L)

            c.clear()

            self.assertEqual(c.get_value().value,0L)

            f()

            self.assertEqual(c.get_value().value,1L)
        finally:
            unregister_counter(counter=c)


    def test_average_counter_value(self):
        a = AverageCounterValue(1)
        b = AverageCounterValue(3)
        a.merge_with(b)
        self.assertEquals(a.value,2.0)

    def test_accumulative_counter_value(self):
        a = AccumulativeCounterValue(1)
        b = AccumulativeCounterValue(3)
        a.merge_with(b)
        self.assertEquals(a.value,4)

    def test_min_counter_value(self):
        a = MinCounterValue(1)
        b = MinCounterValue(3)
        a.merge_with(b)
        self.assertEquals(a.value,1)
        c = MinCounterValue(0)
        a.merge_with(c)
        self.assertEquals(a.value,0)
        b.value = None
        a.merge_with(b)
        self.assertEquals(a.value,0)

    def test_max_counter_value(self):
        a = MaxCounterValue(3)
        b = MaxCounterValue(1)
        a.merge_with(b)
        self.assertEquals(a.value,3)
        c = MaxCounterValue(4)
        a.merge_with(c)
        self.assertEquals(a.value,4)
        b.value = None
        a.merge_with(b)
        self.assertEquals(a.value,4)


    def test_process_elections(self):
        debug_log = None # logging.getLogger("election")

        statuses = [None,None,None]

        def node(id):
            leader = CollectingLeader(port=1234,debug_log=debug_log)
            node = CollectingNode(None,None,port=1234,debug_log=debug_log)
            (status,node_err,leader_err)=elect_leader(node,leader)
            if debug_log: debug_log.info("status for me %s","leader" if status else "node")
            statuses[id]=status

            while None in statuses:
                if debug_log: debug_log.info("Waiting: statuses sor far %s",repr(statuses))
                sleep(0.1)

            if status:
                leader.stop_leading()
            else:
                node.close()
        


        p1 = threading.Thread(target=node,args=(0,))
        p1.daemon=True
        p2 = threading.Thread(target=node,args=(1,))
        p2.daemon=True
        p3 = threading.Thread(target=node,args=(2,))
        p3.daemon=True
        p1.start();
        p2.start();
        p3.start()
        p1.join();
        p2.join();
        p3.join()

        self.assertEqual(sorted(statuses),[False,False,True])

    def test_auto_reelection(self):
        debug_log = None #;logging.getLogger("reelection")
        node1 = MultiprocessReporterBase(collecting_port=4567,debug_log=debug_log,role=ReportingRole.AUTO_ROLE)
        node2 = MultiprocessReporterBase(collecting_port=4567,debug_log=debug_log,role=ReportingRole.AUTO_ROLE)
        node3 = MultiprocessReporterBase(collecting_port=4567,debug_log=debug_log,role=ReportingRole.AUTO_ROLE)
        try:
            self.assertEqual(node1.actual_role,ReportingRole.LEADER_ROLE)
            self.assertEqual(node2.actual_role,ReportingRole.NODE_ROLE)
            self.assertEqual(node3.actual_role,ReportingRole.NODE_ROLE)
            if debug_log:
                debug_log.info("Shutting down leader")

            #switch port to avoid TIME_WAIT issues in tests
            node2.leader.port = 8902
            node2.node.port = 8902
            node3.leader.port = 8902
            node3.node.port = 8902

            node1.shutdown() # this should cause re-election.
            node1=None
            sleep(0.5)
            roles = [node2.actual_role,node3.actual_role]
            self.assertEqual(sorted(roles),[0,1]) # there is a leader again

        finally:
            if node1:
                node1.node.close()
            node2.node.close()
            node3.node.close()
            if node1:
                node1.leader.stop_leading()
            node2.leader.stop_leading()
            node3.leader.stop_leading()

            



    def test_basic_collections(self):
        debug_log = None #logging.getLogger("collection")

        vals = {}
        def make_node(val):
            class fake_node(MultiprocessReporterBase):
                def node_get_values(self):
                    c = CounterValueCollection()
                    c["val"]=AccumulativeCounterValue(val)
                    return c

                def _output_report(self,counter_values_col):
                    vals.update(counter_values_col)

            return  fake_node

        # first define leader so people have things to connect to.
        leader = make_node(4)(collecting_port=60907,debug_log=debug_log,role=ReportingRole.LEADER_ROLE)
        try:
            node1 = make_node(1)(collecting_port=60907,debug_log=debug_log,role=ReportingRole.NODE_ROLE)
            node2 = make_node(2)(collecting_port=60907,debug_log=debug_log,role=ReportingRole.NODE_ROLE)
            node3 = make_node(3)(collecting_port=60907,debug_log=debug_log,role=ReportingRole.NODE_ROLE)
            leader.report()
            self.assertEqual(vals["val"],1+2+3+4)

            self.assertEqual(sorted([r["val"] for r in vals["__node_reports__"].values()])
                             , [1,2,3,4])
        except Exception as e:
            if debug_log:
                debug_log.error(e)

            raise
        finally:
            if debug_log:
                debug_log.info("Shutting done nodes")
            node1.shutdown()
            node2.shutdown()
            node3.shutdown()

            if debug_log:
                debug_log.info("Shutting done leader")
            leader.shutdown()




if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG,format="%(asctime)s | %(process)d|%(thread)d | %(name)s | %(levelname)s | %(message)s")

    unittest.main()
