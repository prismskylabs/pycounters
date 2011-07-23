"""
    a small utility to write munin plugins based on the output of the JSONFile reporter

    example usage:

    munin_plugin.py:
    #!/usr/bin/python

    from pycounters.utils.munin import Plugin

    config = [
        {
            "id" : "graph_id"
            "global" : {
                # graph global options: http://munin-monitoring.org/wiki/protocol-config
                "title" : "Title"
                "info"  : "Some info"
                "category" : "PyCounters"
            }
            "data" : [
                {
                    "counter" : "Somepycountername"
                    "label"   : "A human redable form"
                    "draw"    : "LINE2"
                }
                #...

            ]
        }
    ]

    p = Plugin("output_file.json",config) # initialize the plugin

    p.process_cmd() # process munin command and output requested data or config

"""
import sys
from .. import reporters

def _fprint(fmt,*args):
    print(fmt % args)

class Plugin(object):

    def __init__(self,json_output_file=None,config=None):
        self.output_file = json_output_file
        self.config = config


    def output_data(self):
        """ executes the data command
        """

        values = reporters.JSONFileReporter.safe_read(self.output_file)
        for graph in self.config:
            if not graph.get("id"):
                raise Exception("Missing graph id")
            _fprint("multigraph %s",graph["id"])
            for data in graph.get("data"):
                counter = data.get("counter")
                v = values.get(counter)
                if v is not None:
                    _fprint("%s.value %s",counter,v)



    def output_config(self):
        """ executes the config command
        """
        for graph in self.config:
            if not graph.get("id"):
                raise Exception("Missing graph id")
            _fprint("multigraph %s",graph["id"])
            for g_opt,g_val in graph.get("global",{}).iteritems():
                _fprint("graph_%s %s",g_opt,g_val)

            for data in graph.get("data"):
                counter = data.get("counter")
                if not counter:
                    raise Exception("Missing counter key in data part of graph %s",graph["id"])

                for g_opt,g_val in data.iteritems():
                    if g_opt == "counter":
                        continue
                    _fprint("%s.%s %s",counter,g_opt,g_val)


            _fprint("")
                                    

    def process_cmd(self):
        """process munin command and output requested data or config"""
        if sys.argv[-1] == 'config':
            self.output_config()
        else:
            self.output_data()
