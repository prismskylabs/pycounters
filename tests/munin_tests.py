import os
import unittest

from pycounters import register_counter, unregister_counter
from pycounters.counters import EventCounter
from pycounters.reporters import JSONFileReporter
from pycounters.utils import munin


class MuninTests(unittest.TestCase):
    def test_munin(self):
        cfg = [
                {
                    "id": "test",
                    "global": dict(title="T"),
                    "data": [
                        dict(counter="test1", label="Test")
                    ]
                }
        ]

        filename = "/tmp/json_test.txt"

        output = []

        def fake_print(fmt, *args):
            output.append(fmt % args)

        munin._fprint = fake_print
        plugin = munin.Plugin(json_output_file=filename, config=cfg)

        plugin.output_config(cfg)

        self.assertEqual(output, [
            "multigraph test", "graph_title T", "test1.label Test", ""
        ])

        while output:
            output.pop()

        jsfr = JSONFileReporter(output_file=filename)
        test1 = EventCounter("test1")
        register_counter(test1)
        try:
            test1.report_event("test1", "value", 2)

            jsfr.report()

            plugin.output_data(cfg)
            self.assertEqual(output, ["multigraph test", "test1.value 2"])

            os.unlink(filename)
        finally:
            unregister_counter(counter=test1)