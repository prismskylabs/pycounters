.. PyCounters documentation master file, created by
   sphinx-quickstart on Fri Jun  3 15:32:05 2011.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

==========================================
PyCounters - instrumenting production code
==========================================

A light weight library to monitor performance and events in production systems.
 
-----------------
Typical use cases
-----------------

 * Number of items/requests processed per second.
 * Average processing time of items.
 * Average waiting time on resources/locks.
 * Time spent in DB layer.
 * Cache hit/miss rates.


.. _simple_examples:

--------------------
Some simple examples
--------------------

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Measuring execution frequency
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Count the number of times per second a function is executed::

    from pycounters.shortcuts import frequency

    @frequency()
    def f():
        """ some interesting work like serving a request """
        pass

.. note:: Measurements are done by averaging out a sliding window of 5 minutes. Window size is configurable.

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Measuring average executing time
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Count the average wall clock time a function runs::

    from pycounters.shortcuts import time

    @time()
    def f():
        """ some interesting work like serving a request """
        pass

.. note:: You need to specify the name of the counter to be used. This allows for counting multiple function using a single counter

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Measuring custom event frequency
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Counting some event somewhere in your code::

    from pycounters.shortcuts import occurrence

    def some_code():
        ...
        if TEST_FOR_SOMETHING:
            occurrence("event_name")
        ...

---------------------------------
Nice, but is it just that simple?
---------------------------------

Well, almost (see :ref:`moving_parts` for a complete answer.) To let the counters report their statistics you need
to initialize an instance of the LogReporter: ::

    import pycounters
    import logging

    reporter=pycounters.reporters.LogReporter(logging.getLogger("counters"))
    pycounters.register_reporter(reporter)
    pycounters.start_auto_reporting(seconds=300)

Once adding this code, all the counters will periodically report their stats to a log named "counters".
Here is an example: ::

    2011-06-03 18:12:44,881 | 9130|1286490432 | counters | INFO | posting 0.589342236519
    2011-06-03 18:12:44,888 | 9130|1286490432 | counters | INFO | search 1.47849245866

.. note:: The above logs indicate that the search function took 1.48 seconds on average to execute. The posting function
    took only 0.59 seconds.

-----------------------------------
Installation
-----------------------------------

Easy install PyCounters to get it up and running: ::

    easy_install pycounters

Take a look at the :ref:`tutorial` for more details.

----------------------------------
Cool, but it would be great if ...
----------------------------------

PyCounters is in it's early stages. If you have any ideas for improvements, features which are aboslutely a must or things
you feel are outright stupid - I'd love to hear. Make ticket on https://bitbucket.org/bleskes/pycounters/issues .

Here is what I have in mind so far:
 * `Django <http://www.djangoproject.com/>`_ integration (I'm currently working on this)
 * `Geckoboard <http://www.geckoboard.com>`_ output

Of course, you are more then welcome to browse and/or fork the code: https://bitbucket.org/bleskes/pycounters



---------------
Further reading
---------------

.. toctree::
   :maxdepth: 3

   tutorial
   moving_parts
   reference
   utilities

