.. _moving_parts:

=================
Moving Parts
=================

PyCounters architecture is built arround three main concepts:
 * :ref:`events` reporting (start and end of functions, numerical values etc.)
 * :ref:`counters` for collecting the above events and analyzing them (on demand).
 * :ref:`reporters` for outputing the collected statistics.


In short, PyCounters is built to allow adding event reporting with pratically no perfomance impact.
Counters add some minimal overhead. Only on output does PyCounters do some calculation (every 5 minutes, depending on configuration).

When using PyCounters, consider the following:
 * Triggering events is extremly lite weight. All events with no corresponding Counters are ignored.
 * Therefore you can add as many events as you want.
 * Counters can be registered and unregistered on demand. Only collect what you need.
 * Outputing is a relatively rare event - don't worry about the calculation it does.

.. _events:

--------------------
Events
--------------------

.. py:currentmodule:: pycounters

PyCounters define 2 types of events:

start & end events
    Start and end events are used to report the start and end of a function or any other process.
    These events are typically caught by timing counters but anything is possible.
    Start and end events can be reported through the :func:`report_start` , :func:`report_end` or the :func:`report_start_end` \
    decorator.

value events
    These events report a value to the counters. You typically use these to track averages of things
    but you can get creative. For example - reporting 1 on a cache hit and 0 on a cache miss to an AverageWindowCounter
    will give you the average precentage of cache hits.
    Value events can be reported by using the :func:`report_value` function.

.. _counters:

--------------------
Counters
--------------------

All the "smartness" of PyCounters is bundeled withing a set of Counters. Counters are in charge of intercepting and interpeting
events reported by different parts of the program. As mentioned before, you can register a Counter when you want to analyse events
with identical name. You do so by using the :py:func:`register_counter` function: ::

    counter = AverageWindowCounter("some_name")
    register_counter(counter)


You can also unregister the counter once you don't need it anymore: ::

    unregister_counter(counter=counter)

or by name::

    unregister_counter(name="some_name")

.. note:: After unregistering the counter all events with "some_name".
.. note:: Currently, you can only register a single counter for any given name.



.. _reporters:

--------------------
Reporters
--------------------

Reportes are the way to collect a report from the currently registered Counters. Reporters are not supposed to run often as that
will have a performance impact.

At the moment PyCounters can only output to python logs. You do so by creating an instance of :py:obj:`LogReporter` and
turning auto reporting on (using :py:meth:`LogReporter.start_auto_report` .)


---------------------
Shortcuts
---------------------

All the :ref:`simple_examples` in the main documentation page used shortcuts functions. These are functions which both report
events and auto add the most common Counter for them. See :ref:`shortcut_functions` for details.

