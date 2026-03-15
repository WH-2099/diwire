.. meta::
   :description: How to use diwire with django-modern-rest controllers: request-scoped injection via RequestContextMiddleware and add_request_context(container).
   :keywords: django-modern-rest dependency injection, dmr dependency injection, django request scope, python dependency injection django

django-modern-rest
==================

``django-modern-rest`` is built on top of Django's regular request lifecycle, so the diwire
integration is the same one you use for plain Django views:

- :class:`diwire.integrations.django.RequestContextMiddleware` stores the current
  :class:`django.http.HttpRequest` in a ``contextvars.ContextVar`` for the duration of a request.
- :func:`diwire.integrations.django.add_request_context` registers ``HttpRequest`` in your
  :class:`diwire.Container`, so controller methods and request-scoped services can depend on it.

The package is installed from PyPI as ``django-modern-rest``, but current releases expose their
runtime API from the ``dmr`` module.

Minimal setup
-------------

.. code-block:: python

   # settings.py
   MIDDLEWARE = [
       # ...
       "diwire.integrations.django.RequestContextMiddleware",
       # ...
   ]

.. literalinclude:: _snippets/django_modern_rest.txt
   :language: python

Inject ``HttpRequest`` in controllers and services
--------------------------------------------------

``django-modern-rest`` controllers are regular Django ``View`` subclasses, so diwire works well
on controller methods decorated with ``@resolver_context.inject(scope=Scope.REQUEST)``.

This gives you the same benefits as plain Django integration:

- inject the active request directly into controller methods
- inject the same request into request-scoped services

Response handling
-----------------

``django-modern-rest`` validates and serializes controller responses. Prefer returning typed data
or using controller helpers like ``self.to_response(...)`` / ``self.to_error(...)`` instead of
constructing raw Django ``HttpResponse`` objects yourself.

Testing
-------

For in-process tests, you can use :class:`dmr.test.DMRClient` (or Django's normal test client) and
keep the same diwire setup: install ``RequestContextMiddleware``, call
``add_request_context(container)``, and route your controller with ``.as_view()``.

.. literalinclude:: _snippets/django_modern_rest_test.txt
   :language: python

How it works
------------

1. Django receives a request and executes ``RequestContextMiddleware``.
2. The middleware stores the active ``HttpRequest`` in a ``ContextVar``.
3. ``django-modern-rest`` instantiates the controller and dispatches the matching endpoint.
4. ``@resolver_context.inject(scope=Scope.REQUEST)`` opens a request scope, resolves
   ``Injected[...]`` parameters, and calls the controller method.
5. After the controller method returns, the injected wrapper ends request-scoped resolution and the
   middleware resets request context.
