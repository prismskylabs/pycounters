.. _moving_parts:

=================
Moving Parts
=================

PyCounters architecture is built around three main concepts:
 * :ref:`events` reporting (start and end of functions, numerical values etc.)
 * :ref:`counters` for collecting the above events and analyzing them (on demand).
 * :ref:`reporters` for outputting the collected statistics.


In short, PyCounters is built to allow adding event reporting with piratically no performance impact.
Counters add some minimal overhead. Only on output does PyCounters do some calculation (every 5 minutes, depending on configuration).

When using PyCounters, consider the following:
 * Triggering events is extremely lite weight. All events with no corresponding Counters are ignored.
 * Therefore you can add as many events as you want.
 * Counters can be registered and unregistered on demand. Only collect what you need.
 * Outputting is a relatively rare event - don't worry about the calculation it does.

.. _events:

--------------------
Events
--------------------

.. py:currentmodule:: pycounters

PyCounters defines two types of events:

start and end events
    Start and end events are used to report the start and end of a function or any other block of code.
    These events are typically caught by timing counters but anything is possible.
    Start and end events should be reported through the :func:`report_start` , :func:`report_end` or the :func:`report_start_end` \
    decorator.

value events
    These events report a value to the counters. You typically use these to track averages of things
    but you can get creative. For example - reporting 1 on a cache hit and 0 on a cache miss to an AverageWindowCounter
    will give you the average rate of cache hits.
    Value events can be reported by using the :func:`report_value` function.

.. _counters:

--------------------
Counters
--------------------

All the "smartness" of PyCounters is bundled withing a set of Counters. Counters are in charge of intercepting and interpreting
events reported by different parts of the program. As mentioned before, you can register a Counter when you want to analyze specific events
(by default events of identical name). You do so by using the :py:func:`register_counter` function: ::

    counter = AverageWindowCounter("some_name")
    register_counter(counter)


You can also unregister the counter once you don't need it anymore: ::

    unregister_counter(counter=counter)

or by name::

    unregister_counter(name="some_name")

.. note:: After unregistering the counter all events named "some_name" will be ignored (unless some other counter listens to them).
.. note:: You can only register a single counter for any given name.



.. _reporters:

--------------------
Reporters
--------------------


.. py:currentmodule:: pycounters.reporters

Reporters are used to collect a report from the currently registered Counters. Reporters are not supposed to run often as that
will have a performance impact.

At the moment PyCounters can only output to python logs and JSON files. For example, to output to logs, create
an instance of :obj:`LogReporter <pycounters.reporters.LogReporter>` . You can then manually output reports
(using :func:`output_report <pycounters.output_report>`) or
turn on auto reporting (using :func:`start_auto_reporting <pycounters.start_auto_reporting>` .) ::

    reporter=pycounters.reporters.LogReporter(logging.getLogger("counters"))
    pycounters.register_reporter(reporter)
    #... some where later
    pycounters.output_report()




.. _shortcuts:

---------------------
Shortcuts
---------------------

These are functions which both report
events and auto add the most common Counter for them. See :ref:`shortcut_functions` for more details and :ref:`simple_examples`
in the main documentation page for usage examples.

