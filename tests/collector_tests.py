import logging
import unittest
import threading
from time import sleep
from pycounters import register_counter, register_reporter, report_value, unregister_counter, unregister_reporter, output_report

from pycounters.base import CounterValueCollection
from pycounters.counters import TotalCounter
from pycounters.counters.values import AccumulativeCounterValue
from pycounters.reporters.base import CollectingRole, MultiProcessCounterValueCollector
from pycounters.reporters.tcpcollection import CollectingLeader, CollectingNode, elect_leader
from tests.counter_tests import SimpleValueReporter


class CollectorTests(unittest.TestCase):

    def test_basic_collection(self):
        test1 = TotalCounter("test1")
        register_counter(test1)
        test2 = TotalCounter("test2")
        register_counter(test2)

        v = SimpleValueReporter()
        register_reporter(v)

        report_value("test1", 1)
        report_value("test2", 2)
        output_report()
        self.assertTrue("__collection_time__" in v.last_values)
        self.assertEquals(v.values_wo_metadata,dict(test1=1,test2=2))

        unregister_counter(counter=test1)
        unregister_counter(counter=test2)

        unregister_reporter(reporter=v)

    def test_basic_multi_proccess_collections(self):
        debug_log = None  # logging.getLogger("collection")


        def make_node(val):
            class fake_node(MultiProcessCounterValueCollector):
                def node_get_values(self):
                    c = CounterValueCollection()
                    c["val"] = AccumulativeCounterValue(val)
                    return c



            return  fake_node

        # first define leader so people have things to connect to.
        leader = make_node(4)(collecting_address=("", 60907), debug_log=debug_log, role=CollectingRole.LEADER_ROLE)

        try:
            node1 = make_node(1)(collecting_address=("", 60907), debug_log=debug_log, role=CollectingRole.NODE_ROLE)
            node2 = make_node(2)(collecting_address=("", 60907), debug_log=debug_log, role=CollectingRole.NODE_ROLE)
            node3 = make_node(3)(collecting_address=("", 60907), debug_log=debug_log, role=CollectingRole.NODE_ROLE)
            vals = leader.get_values()
            self.assertEqual(vals["val"], 1 + 2 + 3 + 4)

            self.assertEqual(sorted([r["val"] for r in vals["__node_reports__"].values()]),
                [1, 2, 3, 4])
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

    def test_process_elections(self):
        debug_log = None  # logging.getLogger("election")

        statuses = [None, None, None]

        def node(id):
            leader = CollectingLeader(hosts_and_ports=[("", 1234)], debug_log=debug_log)
            node = CollectingNode(None, None, hosts_and_ports=[("", 1234)], debug_log=debug_log)
            (status, node_err, leader_err) = elect_leader(node, leader)
            if debug_log:
                debug_log.info("status for me %s", "leader" if status else "node")
            statuses[id] = status

            while None in statuses:
                if debug_log:
                    debug_log.info("Waiting: statuses sor far %s", repr(statuses))
                sleep(0.1)

            if status:
                leader.stop_leading()
            else:
                node.close()

        p1 = threading.Thread(target=node, args=(0, ))
        p1.daemon = True
        p2 = threading.Thread(target=node, args=(1, ))
        p2.daemon = True
        p3 = threading.Thread(target=node, args=(2, ))
        p3.daemon = True
        p1.start()
        p2.start()
        p3.start()
        p1.join()
        p2.join()
        p3.join()

        self.assertEqual(sorted(statuses), [False, False, True])

    def test_auto_reelection(self):
        debug_log = None #logging.getLogger("reelection")
        node1 = MultiProcessCounterValueCollector(collecting_address=[("", 4567), ("", 4568)], debug_log=debug_log,
                    role=CollectingRole.AUTO_ROLE)
        node2 = MultiProcessCounterValueCollector(collecting_address=[("", 4567), ("", 4568)], debug_log=debug_log,
                    role=CollectingRole.AUTO_ROLE)
        node3 = MultiProcessCounterValueCollector(collecting_address=[("", 4567), ("", 4568)], debug_log=debug_log,
                    role=CollectingRole.AUTO_ROLE)
        try:
            self.assertEqual(node1.actual_role, CollectingRole.LEADER_ROLE)
            self.assertEqual(node2.actual_role, CollectingRole.NODE_ROLE)
            self.assertEqual(node3.actual_role, CollectingRole.NODE_ROLE)
            if debug_log:
                debug_log.info("Shutting down leader")

            node1.shutdown() # this should cause re-election.
            node1 = None
            sleep(0.5)
            with node2.lock:
                pass ## causes to wait until node2 finished re-electing
            with node3.lock:
                pass ## causes to wait until node2 finished re-electing

            roles = [node2.actual_role, node3.actual_role]
            self.assertEqual(sorted(roles), [0, 1]) # there is a leader again

        finally:
            if node1:
                node1.node.close()
            node2.node.close() # shutting down nodes first to avoid re-election..
            node3.node.close()
            if node1:
                node1.shutdown()
            node2.shutdown()
            node3.shutdown()

    def test_auto_server_upgrade_auto_role_simple(self):
        debug_log = None #logging.getLogger("upgrade_auto")
        node1 = MultiProcessCounterValueCollector(collecting_address=[("", 5568)], debug_log=debug_log,
            role=CollectingRole.AUTO_ROLE)
        node2 = MultiProcessCounterValueCollector(collecting_address=[("", 5567), ("", 5568)], debug_log=debug_log,
            role=CollectingRole.AUTO_ROLE)

        try:
            self.assertEqual(node1.actual_role, CollectingRole.LEADER_ROLE)
            self.assertEqual(node2.actual_role, CollectingRole.NODE_ROLE)

            if debug_log:
                debug_log.info("Telling the leader it's on a lower level")

            node1.collecting_address = [("", 5567), ("", 5568)]
            node1.leader.leading_level = 1
            node1.node.hosts_and_ports = node1.collecting_address

            node1._auto_upgrade_server_level_target(wait_time=10)

            sleep(0.5)
            self.assertEqual(node1.leader.leading_level, 0)

            with node2.lock: ## wait for node2 to stablize..
                pass

            self.assertEqual(node2.actual_role, CollectingRole.NODE_ROLE)
        finally:
            node2.shutdown()
            node1.shutdown()

    def test_auto_server_upgrade_auto_role_switching_roles(self):
        debug_log = None #logging.getLogger("upgrade_switch")
        node1 = MultiProcessCounterValueCollector(collecting_address=[("", 7568)], debug_log=debug_log,
                    role=CollectingRole.AUTO_ROLE)
        node2 = MultiProcessCounterValueCollector(collecting_address=[("", 7567), ("", 7568)], debug_log=debug_log,
                    role=CollectingRole.AUTO_ROLE)
        try:
            self.assertEqual(node1.actual_role, CollectingRole.LEADER_ROLE)
            self.assertEqual(node2.actual_role, CollectingRole.NODE_ROLE)

            node3 = MultiProcessCounterValueCollector(collecting_address=[("", 7567)], debug_log=debug_log,
                role=CollectingRole.AUTO_ROLE)
            self.assertEqual(node3.actual_role, CollectingRole.LEADER_ROLE)

            if debug_log:
                debug_log.info("Telling the leader it's on a lower level")

            node1.collecting_address = [("", 7567), ("", 7568)]
            node1.leader.leading_level = 1
            node1.node.hosts_and_ports = node1.collecting_address

            if debug_log:
                debug_log.info("Upgrading leader level")
            node1._auto_upgrade_server_level_target(wait_time=10)

            sleep(0.5)
            if debug_log:
                debug_log.info("Checking node 1 became a node")
            self.assertEqual(node1.actual_role, CollectingRole.NODE_ROLE)

            with node2.lock: ## wait for node2 to stablize..
                pass

            self.assertEqual(node2.actual_role, CollectingRole.NODE_ROLE)

        finally:
            node2.shutdown()
            node1.shutdown()
            node3.shutdown()
