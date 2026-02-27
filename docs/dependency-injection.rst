.. meta::
   :description: A practical introduction to dependency injection (DI) in Python: what it is, why it helps, trade-offs, and how diwire approaches DI.
   :keywords: dependency injection, python dependency injection, inversion of control, ioc container, service locator, testing

Dependency injection (DI)
=========================

Dependency injection (DI) is a way to build objects by **passing dependencies in**, instead of having objects reach out
to globals/singletons. You typically see it as *constructor injection*:

.. code-block:: python

   class Service:
       def __init__(self, repo: "Repo") -> None:
           self._repo = repo

The *container* (or your application wiring code) is responsible for constructing ``Repo`` and then passing it into
``Service``.

Why people use DI
-----------------

DI is mostly about keeping codebases maintainable as they grow:

- **Explicit dependencies**: the class signature tells you what it needs.
- **Testability**: swap real dependencies for fakes/stubs in unit tests.
- **Separation of concerns**: domain code doesn't need to know how infrastructure is created.
- **Lifecycle management**: create and clean up resources (DB sessions, HTTP clients) at predictable boundaries.

Trade-offs (and when *not* to use DI)
-------------------------------------

DI is not required for every project.

You might skip DI when:

- the codebase is small and a little duplication is cheaper than abstraction
- you don't have lifecycle-heavy resources (no DB sessions, no background workers)
- you're fighting the container more than you're getting value from it

DI can also be overused. A good heuristic is to keep DI at **module boundaries** (web handlers, tasks, CLI entrypoints)
and let most of your internal code be plain Python objects with normal constructors.

DI vs. service locator
----------------------

DI is sometimes confused with the *service locator* pattern, where objects ask a global container for dependencies at
runtime.

Service locator tends to:

- hide dependencies (they don't show up in signatures)
- make tests harder (everything depends on global state)
- spread container knowledge across the codebase

diwire nudges you toward explicit dependencies by building graphs from type hints and keeping injected parameters
visible (for example via ``Injected[T]`` on handler functions).

How diwire fits
---------------

diwire is a type-driven DI container for Python 3.10+.

Its design goals:

- **Small public API**: one container and a few primitives (scopes, lifetimes, components).
- **Type-first wiring**: dependencies come from annotations, so many graphs need little to no registration code.
- **Deterministic cleanup**: generator/async-generator providers clean up on scope exit.
- **Performance without magic**: ``compile()`` precomputes the graph for fast steady-state resolution.

If you want to see DI in a framework context, start with :doc:`quickstart-fastapi`.
If you prefer learning from runnable scripts, start with :doc:`howto/examples/index`.
