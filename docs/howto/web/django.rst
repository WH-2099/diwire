.. meta::
   :description: How to use diwire with Django: request-scoped injection via RequestContextMiddleware and add_request_context(container).
   :keywords: django dependency injection, python dependency injection django, request scope dependency injection

Django
======

The Django integration provides request-scoped dependency resolution for views using the same
``Injected[T]`` pattern as other diwire web integrations.

If your Django views are implemented with ``django-modern-rest`` controllers, see
:doc:`django-modern-rest`.

Minimal setup
-------------

The integration consists of two pieces:

- :class:`diwire.integrations.django.RequestContextMiddleware` stores the current
  :class:`django.http.HttpRequest` in a ``contextvars.ContextVar`` for the duration of a request.
- :func:`diwire.integrations.django.add_request_context` registers ``HttpRequest`` in your
  :class:`diwire.Container`, so services can depend on the active request.

.. code-block:: python

   # settings.py
   MIDDLEWARE = [
       # ...
       "diwire.integrations.django.RequestContextMiddleware",
       # ...
   ]

.. code-block:: python

   from django.http import HttpRequest, JsonResponse

   from diwire import Container, Injected, Lifetime, Scope, resolver_context
   from diwire.integrations.django import add_request_context

   container = Container()
   add_request_context(container)


   class RequestService:
       def run(self) -> str:
           return "ok"


   container.add(
       RequestService,
       provides=RequestService,
       scope=Scope.REQUEST,
       lifetime=Lifetime.SCOPED,
   )


   @resolver_context.inject(scope=Scope.REQUEST)
   def health(
       request: HttpRequest,
       service: Injected[RequestService],
   ) -> JsonResponse:
       _ = request
       return JsonResponse({"status": service.run()})

Inject ``HttpRequest`` in views and services
--------------------------------------------

With middleware + container registration in place, you can inject the active request directly
and into request-scoped services.

.. code-block:: python

   from dataclasses import dataclass

   from django.http import HttpRequest, JsonResponse

   from diwire import Container, Injected, Lifetime, Scope, resolver_context
   from diwire.integrations.django import add_request_context

   container = Container()
   add_request_context(container)


   @dataclass
   class RequestPathService:
       request: HttpRequest

       def path(self) -> str:
           return self.request.path


   container.add(
       RequestPathService,
       provides=RequestPathService,
       scope=Scope.REQUEST,
       lifetime=Lifetime.SCOPED,
   )


   @resolver_context.inject(scope=Scope.REQUEST)
   def path_view(
       request: HttpRequest,
       resolved_request: Injected[HttpRequest],
       service: Injected[RequestPathService],
   ) -> JsonResponse:
       _ = request
       return JsonResponse(
           {
               "direct_path": resolved_request.path,
               "service_path": service.path(),
           }
       )

How it works
------------

1. Django receives a request and executes ``RequestContextMiddleware``.
2. The middleware stores the active ``HttpRequest`` in a ``ContextVar``.
3. ``@resolver_context.inject(scope=Scope.REQUEST)`` opens a request scope, resolves
   ``Injected[...]`` parameters, and calls your view.
4. After the view returns (or raises), the middleware resets request context and the injected
   wrapper closes the scope, triggering deterministic cleanup for scoped providers.

If you forget the middleware, resolving ``HttpRequest`` from the container raises
:class:`diwire.exceptions.DIWireIntegrationError`.

Testing
-------

- In-process tests: execute middleware + decorated views directly, or use Django's test client, and
  ensure your app includes ``RequestContextMiddleware`` and calls
  ``add_request_context(container)`` in setup.
