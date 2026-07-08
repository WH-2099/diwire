.. meta::
   :description: diwire pytest plugin integration example.

Pytest plugin
=============

What you'll learn
-----------------

- Enable ``diwire.integrations.pytest_plugin`` for ``Injected[T]`` test parameters.
- Inject ``AsyncProvider[T]`` into async tests and apply per-test overrides.

Run locally
-----------

.. code-block:: bash

   uv run python examples/ex_14_pytest_plugin/01_pytest_plugin.py

Example
-------

.. literalinclude:: ../../../examples/ex_14_pytest_plugin/01_pytest_plugin.py
   :language: python
   :class: diwire-example

.. literalinclude:: ../../../examples/ex_14_pytest_plugin/test_demo.py
   :language: python
   :class: diwire-example
