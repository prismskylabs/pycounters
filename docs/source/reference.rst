

==============================
Object and function reference
==============================

.. py:module:: pycounters

.. _event_reporting:

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

.. autoclass:: TotalCounter
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
Reporters
------------------

.. py:currentmodule:: pycounters.reporters

.. autoclass:: LogReporter
    :members:
    :inherited-members:


.. autoclass:: JSONFileReporter
    :members:
    :inherited-members:

.. py:currentmodule:: pycounters

.. autofunction:: register_reporter

.. autofunction:: unregister_reporter


.. autofunction:: start_auto_reporting



^^^^^^^^^^^^^^^^^^^^^^^
Multi-process reporting
^^^^^^^^^^^^^^^^^^^^^^^

.. py:currentmodule:: pycounters

.. autofunction:: configure_multi_process_collection

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

.. automodule::  pycounters.shortcuts
    :members:
    






