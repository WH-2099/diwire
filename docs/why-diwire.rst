.. meta::
   :description: Why diwire exists: type-driven DI with a small API, deterministic cleanup, and fast steady-state resolution.
   :keywords: dependency injection python, type driven dependency injection, type hints dependency injection, ioc container python

Why diwire
==========

diwire is built for teams that want dependency injection to feel like *Python with type hints*, not like a framework.

If your project is small, manual wiring might be the simplest choice. diwire becomes valuable when you have:

- multiple layers (web handlers → services → repositories)
- resources with lifetimes (DB sessions, HTTP clients, transactions)
- the need for fast, deterministic tests (swap dependencies cleanly)

The goals
---------

- **Type-first wiring**: dependencies come from annotations, so most graphs require little to no registration code.
- **Small surface area**: one container, a few primitives (lifetimes, scopes, components), and predictable behavior.
- **Correct cleanup**: resource lifetimes map to scopes via generator/async-generator providers.
- **Async support**: ``aresolve()`` mirrors ``resolve()`` and async providers are first-class.
- **Zero runtime dependencies**: easy to adopt in any environment.
- **Fast steady-state**: compiled resolvers reduce overhead on hot paths.

What makes diwire different
---------------------------

- **Type-driven by default**: constructor signatures are the "wiring language".
- **Scopes are first-class**: request/job scopes are explicit and come with deterministic cleanup.
- **Performance is a feature**: compilation is built-in; benchmarks and methodology are published.
- **Opt-in strict mode**: when you need full control, you can disable autoregistration and fail fast on missing keys.

Stability
---------

diwire targets a stable, small public API.

- Backward-incompatible changes only happen in major releases.
- Deprecations are announced first and kept for at least one minor release (when practical).

What “type-driven” means in practice
------------------------------------

If you can write this:

.. code-block:: python

   from dataclasses import dataclass


   @dataclass
   class Repo:
       ...


   @dataclass
   class Service:
       repo: Repo

...then diwire can resolve ``Service`` by reading type hints and resolving dependencies recursively.

When you need explicit control, you still have it:

- interface/protocol bindings via ``add(..., provides=...)``
- instances via ``add_instance(...)``
- factories (sync/async/generator/context manager)
- lifetimes (``TRANSIENT``, ``SCOPED``) and scope transitions (root-scoped ``SCOPED`` behaves like a singleton)
- named registrations via ``Component("name")``
- open generics

Where to start
--------------

- If you use FastAPI: :doc:`quickstart-fastapi`
- If you want a DI primer first: :doc:`dependency-injection`
- If you want runnable scripts: :doc:`howto/examples/index`

Benchmarks
----------

See :doc:`howto/advanced/performance` for benchmark methodology, reproducible commands, and results.
