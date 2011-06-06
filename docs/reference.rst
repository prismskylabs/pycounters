

==============================
Object and function reference
==============================

.. py:module:: pycounters

-----------------
Event reporting
-----------------

.. autofunction:: report_start

.. autofunction:: report_end

.. autofunction:: report_start_end

.. autofunction:: report_value


------------------
Counters
------------------

.. py:currentmodule:: pycounters.counters


.. autoclass:: EventCounter
    :members:
    :inherited-members:

.. autoclass:: AverageWindowCounter
    :members:
    :inherited-members:

.. autoclass:: AverageTimeCounter
    :members:
    :inherited-members:

.. autoclass:: FrequencyCounter
    :members:
    :inherited-members:

------------------
Counters
------------------

.. py:currentmodule:: pycounters.reporters

.. autoclass:: LogReporter
    :members:
    :inherited-members:

--------------------
Registering counters
--------------------

.. py:currentmodule:: pycounters

.. autofunction:: register_counter

.. autofunction:: unregister_counter


.. _shortcut_functions:

------------------
Shortcut functions
------------------

.. py:currentmodule:: pycounters.shortcuts

.. autofunction:: value

.. autofunction:: occurrence

.. autofunction:: frequency

.. autofunction:: count

.. autofunction:: time

.. autofunction:: value





