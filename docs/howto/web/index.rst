.. meta::
   :description: Integrate diwire with FastAPI, aiohttp, and Celery, plus patterns for Starlette, Flask, and Django.

Web frameworks
==============

diwire is intentionally framework-agnostic.

The common pattern is:

1. Build a :class:`diwire.Container` at app startup.
2. Create a request/job scope per incoming request.
3. Register request/job-specific objects (like the current request or current task data) via factories/contextvars.
4. Use function injection (``Injected[T]``) or ``resolver_context`` to keep handlers clean.

.. toctree::
   :maxdepth: 1

   fastapi
   aiohttp
   celery
   starlette
   flask
   django
