.. meta::
   :description: Integrate diwire with web frameworks: FastAPI, Litestar, aiohttp, and patterns for Starlette, Flask, Django, and more.
   :description: Integrate diwire with web frameworks: official integrations for FastAPI, Litestar, aiohttp, Flask, and Django, plus Celery task injection patterns and guidance for Starlette.

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
   litestar
   aiohttp
   celery
   starlette
   flask
   django
