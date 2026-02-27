.. meta::
   :description: Suggested learning paths for diwire: beginner, intermediate, and advanced routes through the documentation.
   :keywords: diwire documentation, dependency injection tutorial, scopes, lifetimes, fastapi dependency injection

Learning paths
==============

Different people come to DI for different reasons. This page suggests a reading order depending on what you need.

If you're using FastAPI
-----------------------

1. :doc:`quickstart-fastapi` (the full pattern in one page)
2. :doc:`howto/web/fastapi` (integration details and testing guidance)
3. :doc:`core/scopes` (what request scopes do and how cleanup works)
4. :doc:`core/function-injection` (how ``Injected[T]`` is resolved)

If you're new to DI (beginner)
------------------------------

1. :doc:`dependency-injection` (what DI is and why teams use it)
2. :doc:`why-diwire` (design goals and what makes diwire different)
3. :doc:`howto/examples/quickstart` (runnable tutorial starting from plain Python)
4. :doc:`core/index` (the mental model behind registrations, scopes, and keys)

If you've used DI containers before (intermediate)
--------------------------------------------------

1. :doc:`core/container` (what gets resolved and how keys work)
2. :doc:`core/registration` (explicit bindings, factories, and instances)
3. :doc:`core/scopes` and :doc:`core/lifetimes` (caching and cleanup)
4. :doc:`howto/index` (frameworks and real-world patterns)

If you care about throughput (advanced)
---------------------------------------

1. :doc:`core/compilation` (what ``compile()`` does)
2. :doc:`howto/advanced/performance` (benchmarks, methodology, and reproduction)
3. :doc:`howto/advanced/concurrency` (lock modes and free-threaded considerations)

When you get stuck
------------------

- :doc:`core/errors` (common errors and how to debug them)
- :doc:`reference/index` (API reference)
