.. meta::
   :description: FastAPI quickstart for diwire: request-scoped injection via @resolver_context.inject(scope=Scope.REQUEST), RequestContextMiddleware, and deterministic cleanup.
   :keywords: fastapi dependency injection, request scope, python dependency injection, ioc container, diwire fastapi

Quick start (FastAPI)
=====================

FastAPI already has a dependency system. diwire is useful when you want:

- a single typed object graph shared across your whole app
- request/job scopes with deterministic cleanup (context managers and generators)
- constructor injection in your services and repositories (no ``Depends`` in every layer)

The pattern
-----------

At a high level:

1. Build a :class:`diwire.Container` at app startup and register your providers.
2. Install :class:`diwire.integrations.fastapi.RequestContextMiddleware` so services can request the active
   :class:`starlette.requests.Request` / :class:`starlette.websockets.WebSocket`.
3. Decorate endpoints with :meth:`diwire.ResolverContext.inject` and annotate injected parameters as
   ``Injected[T]``.

End-to-end example
------------------

This is a single-file FastAPI app with:

- a per-request :class:`DbSession` provided by a generator (deterministic cleanup)
- a nested graph ``UserService -> UserRepository -> DbSession``
- an ``AuditService`` that reads a request header by injecting ``Request``

.. code-block:: python

   from __future__ import annotations

   from collections.abc import Generator
   from dataclasses import dataclass

   from fastapi import FastAPI
   from starlette.requests import Request

   from diwire import Container, Injected, Lifetime, Scope, resolver_context
   from diwire.integrations.fastapi import RequestContextMiddleware, add_request_context

   app = FastAPI()
   app.add_middleware(RequestContextMiddleware)

   container = Container()
   add_request_context(container)


   @dataclass(slots=True)
   class DbSession:
       request_id: str
       closed: bool = False

       def close(self) -> None:
           self.closed = True


   class AuditService:
       def __init__(self, request: Request) -> None:
           self._request = request

       def request_id(self) -> str:
           return self._request.headers.get("x-request-id", "missing")


   def provide_db_session(audit: AuditService) -> Generator[DbSession, None, None]:
       session = DbSession(request_id=audit.request_id())
       try:
           yield session
       finally:
           session.close()


   class UserRepository:
       def __init__(self, session: DbSession) -> None:
           self._session = session

       def get_name(self, user_id: int) -> str:
           _ = self._session
           return f"user-{user_id}"


   class UserService:
       def __init__(self, repo: UserRepository, audit: AuditService) -> None:
           self._repo = repo
           self._audit = audit

       def get_user(self, user_id: int) -> dict[str, int | str]:
           return {
               "id": user_id,
               "name": self._repo.get_name(user_id),
               "request_id": self._audit.request_id(),
           }


   container.add_generator(
       provide_db_session,
       provides=DbSession,
       scope=Scope.REQUEST,
       lifetime=Lifetime.SCOPED,
       require_generator_finally=False,
   )
   container.add(AuditService, scope=Scope.REQUEST, lifetime=Lifetime.SCOPED)
   container.add(UserRepository, scope=Scope.REQUEST, lifetime=Lifetime.SCOPED)
   container.add(UserService, scope=Scope.REQUEST, lifetime=Lifetime.SCOPED)
   container.compile()  # optional, but recommended for stable hot-path performance


   @app.get("/users/{user_id}")
   @resolver_context.inject(scope=Scope.REQUEST)
   def get_user(user_id: int, service: Injected[UserService]) -> dict[str, int | str]:
       return service.get_user(user_id)

Run it locally
--------------

.. code-block:: bash

   uv add diwire fastapi uvicorn
   uv run uvicorn main:app --reload

Common gotchas
--------------

- **Decorator order matters**: apply ``@resolver_context.inject(...)`` *below* the FastAPI decorator so FastAPI sees
  the injected wrapper signature.
- **Request injection needs middleware**: if you inject ``Request``/``WebSocket`` into services, you must install
  :class:`diwire.integrations.fastapi.RequestContextMiddleware` and call
  :func:`diwire.integrations.fastapi.add_request_context`.
- **Scopes are explicit**: use ``scope=Scope.REQUEST`` on ``@resolver_context.inject(...)`` for per-request caching
  and cleanup.

Next steps
----------

- :doc:`howto/web/fastapi` - full FastAPI integration guide (HTTP + WebSocket notes, testing)
- :doc:`core/scopes` - how scopes and cleanup work
- :doc:`core/function-injection` - what ``Injected[T]`` does (including mypy plugin setup for precise typing)

.. note::

   The code block above sets ``require_generator_finally=False`` so it can be executed safely by the documentation
   test suite (which runs code blocks extracted from ``.rst`` files). In normal application code (real ``.py``
   modules), you can keep the default validation enabled.
