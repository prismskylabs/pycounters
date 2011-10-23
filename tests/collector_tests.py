import unittest
import threading
from time import sleep

from pycounters.base import CounterValueCollection
from pycounters.counters.base import AccumulativeCounterValue
from pycounters.reporters.base import ReportingRole, MultiprocessReporterBase
from pycounters.reporters.tcpcollection import CollectingLeader, CollectingNode, elect_leader


class CollectorTests(unittest.TestCase):
    def test_basic_collections(self):
        debug_log = None  # logging.getLogger("collection")
        vals = {}

        def make_node(val):
            class fake_node(MultiprocessReporterBase):
                def node_get_values(self):
                    c = CounterValueCollection()
                    c["val"] = AccumulativeCounterValue(val)
                    return c

                def _output_report(self, counter_values_col):
                    vals.update(counter_values_col)

            return  fake_node

        # first define leader so people have things to connect to.
        leader = make_node(4)(collecting_address=("", 60907), debug_log=debug_log, role=ReportingRole.LEADER_ROLE)

        try:
            node1 = make_node(1)(collecting_address=("", 60907), debug_log=debug_log, role=ReportingRole.NODE_ROLE)
            node2 = make_node(2)(collecting_address=("", 60907), debug_log=debug_log, role=ReportingRole.NODE_ROLE)
            node3 = make_node(3)(collecting_address=("", 60907), debug_log=debug_log, role=ReportingRole.NODE_ROLE)
            leader.report()
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
        debug_log = None  # logging.getLogger("reelection")
        node1 = MultiprocessReporterBase(collecting_address=[("", 4567), ("", 4568)], debug_log=debug_log, role=ReportingRole.AUTO_ROLE)
        node2 = MultiprocessReporterBase(collecting_address=[("", 4567), ("", 4568)], debug_log=debug_log, role=ReportingRole.AUTO_ROLE)
        node3 = MultiprocessReporterBase(collecting_address=[("", 4567), ("", 4568)], debug_log=debug_log, role=ReportingRole.AUTO_ROLE)
        try:
            self.assertEqual(node1.actual_role, ReportingRole.LEADER_ROLE)
            self.assertEqual(node2.actual_role, ReportingRole.NODE_ROLE)
            self.assertEqual(node3.actual_role, ReportingRole.NODE_ROLE)
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
        node1 = MultiprocessReporterBase(collecting_address=[("", 5568)], debug_log=debug_log, role=ReportingRole.AUTO_ROLE)
        node2 = MultiprocessReporterBase(collecting_address=[("", 5567), ("", 5568)], debug_log=debug_log, role=ReportingRole.AUTO_ROLE)
        try:
            self.assertEqual(node1.actual_role, ReportingRole.LEADER_ROLE)
            self.assertEqual(node2.actual_role, ReportingRole.NODE_ROLE)

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

            self.assertEqual(node2.actual_role, ReportingRole.NODE_ROLE)
        finally:
            node2.shutdown()
            node1.shutdown()

    def test_auto_server_upgrade_auto_role_switching_roles(self):
        debug_log = None #logging.getLogger("upgrade_switch")
        node1 = MultiprocessReporterBase(collecting_address=[("", 7568)], debug_log=debug_log, role=ReportingRole.AUTO_ROLE)
        node2 = MultiprocessReporterBase(collecting_address=[("", 7567), ("", 7568)], debug_log=debug_log, role=ReportingRole.AUTO_ROLE)
        try:
            self.assertEqual(node1.actual_role, ReportingRole.LEADER_ROLE)
            self.assertEqual(node2.actual_role, ReportingRole.NODE_ROLE)

            node3 = MultiprocessReporterBase(collecting_address=[("", 7567)], debug_log=debug_log, role=ReportingRole.AUTO_ROLE)
            self.assertEqual(node3.actual_role, ReportingRole.LEADER_ROLE)

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
            self.assertEqual(node1.actual_role, ReportingRole.NODE_ROLE)

            with node2.lock: ## wait for node2 to stablize..
                pass

            self.assertEqual(node2.actual_role, ReportingRole.NODE_ROLE)

        finally:
            node2.shutdown()
            node1.shutdown()
            node3.shutdown()
