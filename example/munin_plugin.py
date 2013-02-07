#!/usr/bin/python

from pycounters.utils.munin import Plugin

config = [
    {
        "id" : "requests_per_sec",
        "global" : {
            # graph global options: http://munin-monitoring.org/wiki/protocol-config
            "title" : "Request Frequency",
            "category" : "PyCounters example"
        },
        "data" : [
            {
                "counter" : "requests_frequency",
                "label"   : "requests per second",
                "draw"    : "LINE2",
            }
        ]
    },
    {
        "id" : "requests_time",
        "global" : {
            # graph global options: http://munin-monitoring.org/wiki/protocol-config
            "title" : "Request Average Handling Time",
            "category" : "PyCounters example"
        },
        "data" : [
            {
                "counter" : "requests_time",
                "label"   : "Average time per request",
                "draw"    : "LINE2",
            }
        ]
    },
    {
        "id" : "requests_total_data",
        "global" : {
            # graph global options: http://munin-monitoring.org/wiki/protocol-config
            "title" : "Total data processed",
            "category" : "PyCounters example"
        },
        "data" : [
            {
                "counter" : "requests_data_len",
                "label"   : "total bytes",
                "draw"    : "LINE2",
            }
        ]
    }

]

p = Plugin("/tmp/server.counters.json",config) # initialize the plugin

p.process_cmd() # process munin command and output requested data or config