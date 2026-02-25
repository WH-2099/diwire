.. meta::
   :description: diwire ContextVar examples: register normal providers that read task-local values.

Scope context values
====================

What you'll learn
-----------------

- Use ``contextvars.ContextVar`` for task-local request values.
- Register normal providers (``add_factory`` / ``add``) that call ``ContextVar.get()``.
- Override values in nested work with ``token = var.set(...)`` and ``var.reset(token)``.

Provider with ContextVar
------------------------

Run locally
~~~~~~~~~~~

.. code-block:: bash

   uv run python examples/ex_17_scope_context_values/01_provider_contextvar.py

.. literalinclude:: ../../../examples/ex_17_scope_context_values/01_provider_contextvar.py
   :language: python
   :class: diwire-example py-run

Nested override with tokens
---------------------------

Run locally
~~~~~~~~~~~

.. code-block:: bash

   uv run python examples/ex_17_scope_context_values/02_nested_scope_inheritance.py

.. literalinclude:: ../../../examples/ex_17_scope_context_values/02_nested_scope_inheritance.py
   :language: python
   :class: diwire-example py-run

Injected callable using ContextVar-backed dependency
----------------------------------------------------

Run locally
~~~~~~~~~~~

.. code-block:: bash

   uv run python examples/ex_17_scope_context_values/03_injected_callable_context.py

.. literalinclude:: ../../../examples/ex_17_scope_context_values/03_injected_callable_context.py
   :language: python
   :class: diwire-example py-run

Annotated provider keys with ContextVar
---------------------------------------

Run locally
~~~~~~~~~~~

.. code-block:: bash

   uv run python examples/ex_17_scope_context_values/04_annotated_context_keys.py

.. literalinclude:: ../../../examples/ex_17_scope_context_values/04_annotated_context_keys.py
   :language: python
   :class: diwire-example py-run

ContextVar defaults without opening scopes
------------------------------------------

Run locally
~~~~~~~~~~~

.. code-block:: bash

   uv run python examples/ex_17_scope_context_values/05_context_without_scope_open.py

.. literalinclude:: ../../../examples/ex_17_scope_context_values/05_context_without_scope_open.py
   :language: python
   :class: diwire-example py-run
