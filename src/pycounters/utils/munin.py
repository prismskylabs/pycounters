"""
    a small utility to write munin plugins based on the output of the JSONFile reporter

    example usage:

    munin_plugin.py:
    #!/usr/bin/python

    from pycounters.utils.munin import Plugin

    config = [
        {
            "id" : "graph_id",
            "global" : {
                # graph global options: http://munin-monitoring.org/wiki/protocol-config
                "title" : "Title",
                "info"  : "Some info",
                "category" : "PyCounters"
            },
            "data" : [
                {
                    "counter" : "Somepycountername",
                    "label"   : "A human redable form",
                    "draw"    : "LINE2"
                }
                #...

            ]
        }
    ]

    p = Plugin("output_file.json", config) # initialize the plugin

    p.process_cmd() # process munin command and output requested data or config

"""
import sys
from .. import reporters
import time


def _fprint(fmt, *args):
    print(fmt % args)


class Plugin(object):
    """
    a small utility to write munin plugins based on the output of the JSONFile reporter

    example usage (munin_plugin.py) : ::

        #!/usr/bin/python

        from pycounters.utils.munin import Plugin

        config = [
            {
                "id" : "graph_id",
                "global" : {
                    # graph global options: http://munin-monitoring.org/wiki/protocol-config
                    "title" : "Title",
                    "info"  : "Some info",
                    "category" : "PyCounters"
                },
                "data" : [
                    {
                        "counter" : "Somepycountername",
                        "label"   : "A human redable form",
                        "draw"    : "LINE2"
                    }
                    #...

                ]
            }
        ]

        p = Plugin("pycounters_output_file.json", config) # initialize the plugin

        p.process_cmd() # process munin command and output requested data or config

    """

    def __init__(self, json_output_file=None, config=None,max_file_age_in_seconds=15*60):
        """
           :param json_output_file: a PyCounter report file generated by the :obj:`pycounters.reporters.JSONFileReporter`
           :param config: a configuration diction defining the different graphs. See class documentation.
           :param max_file_age_in_seconds: reports older than this age are ignored to avoid exporting old data
                to munin. Set to None to disable this functionality.
        """
        self.output_file = json_output_file
        self.config = config
        self.max_file_age_in_seconds = max_file_age_in_seconds

    def counter_id_to_munin_id(self, counter_id):
        return counter_id.replace(" ", "_").replace(".", "_")

    def output_data(self, config):
        """ executes the data command
        """

        values = reporters.JSONFileReporter.safe_read(self.output_file)

        if self.max_file_age_in_seconds:
            collection_time = values.get("__collection_time__",None)
            if collection_time is None:
                raise Exception(("JSON file %s was outputed by an old version of PyCounters, please upgrade to use"+
                                " max_file_age_in_seconds feature.") % (self.output_file,))
            if time.time() - collection_time > self.max_file_age_in_seconds:
                return # json file is too old.

        for graph in config:
            if not graph.get("id"):
                raise Exception("Missing graph id")
            _fprint("multigraph %s", self.counter_id_to_munin_id(graph["id"]))
            for data in graph.get("data"):
                counter = data.get("counter")
                v = values.get(counter)
                if v is not None:
                    _fprint("%s.value %s", self.counter_id_to_munin_id(counter), v)

    def output_config(self, config):
        """ executes the config command
        """
        for graph in config:
            if not graph.get("id"):
                raise Exception("Missing graph id")
            _fprint("multigraph %s", self.counter_id_to_munin_id(graph["id"]))
            for g_opt, g_val in graph.get("global", {}).iteritems():
                _fprint("graph_%s %s", g_opt, g_val)

            for data in graph.get("data"):
                counter = data.get("counter")
                if not counter:
                    raise Exception("Missing counter key in data part of graph %s", graph["id"])

                for g_opt, g_val in data.iteritems():
                    if g_opt == "counter":
                        continue
                    _fprint("%s.%s %s", self.counter_id_to_munin_id(counter), g_opt, g_val)

            _fprint("")

    def process_cmd(self):
        """process munin command and output requested data or config"""
        if sys.argv[-1] == 'config':
            self.output_config(self.config)
        else:
            self.output_data(self.config)
