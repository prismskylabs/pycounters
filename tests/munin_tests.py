import os
import unittest

from pycounters import register_counter, unregister_counter, register_reporter, unregister_reporter
from pycounters.counters import EventCounter
from pycounters.reporters import JSONFileReporter
from pycounters.reporters.base import GLOBAL_REPORTING_CONTROLLER
from pycounters.utils import munin


class MuninTests(unittest.TestCase):

    filename = "/tmp/json_test.txt"


    def make_basic_cfg(self):
        return [
                        {
                            "id": "test",
                            "global": dict(title="T"),
                            "data": [
                                dict(counter="test1", label="Test")
                            ]
                        }
                ]


    def get_last_plugin_output(self):
        return self.output
    def clear_last_plugin_output(self):
        while self.output:
            self.output.pop()

    def create_plugin(self,cfg):
        self.output = []

        def fake_print(fmt, *args):
            self.output.append(fmt % args)

        munin._fprint = fake_print
        return munin.Plugin(json_output_file=self.filename, config=cfg)




    def test_munin_cfg(self):
        cfg = self.make_basic_cfg()
        plugin = self.create_plugin(cfg)
        plugin.output_config(cfg)

        self.assertEqual(self.get_last_plugin_output(), [
            "multigraph test", "graph_title T", "test1.label Test", ""
        ])

    def test_munin_output(self):

        cfg = self.make_basic_cfg()

        plugin = self.create_plugin(cfg)

        jsfr = JSONFileReporter(output_file=self.filename)
        register_reporter(jsfr)
        test1 = EventCounter("test1")
        register_counter(test1)

        try:
            test1.report_event("test1", "value", 2)

            GLOBAL_REPORTING_CONTROLLER.report()

            plugin.output_data(cfg)
            self.assertEqual(self.get_last_plugin_output(), ["multigraph test", "test1.value 2"])

            plugin.max_file_age_in_seconds=0.00001
            self.clear_last_plugin_output()
            plugin.output_data(cfg)
            self.assertEqual(self.get_last_plugin_output(), [])

            plugin.max_file_age_in_seconds=None
            plugin.output_data(cfg)
            self.assertEqual(self.get_last_plugin_output(), ["multigraph test", "test1.value 2"])

            os.unlink(self.filename)
        finally:
            unregister_counter(counter=test1)
            unregister_reporter(jsfr)


