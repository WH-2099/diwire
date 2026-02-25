.. meta::
   :description: Function injection in diwire using Injected[T] and ResolverContext.inject.

Function injection
==================

In addition to constructor injection, diwire can inject dependencies into function parameters.

The building blocks are:

- :class:`diwire.Injected` - a type wrapper used as ``Injected[T]`` to mark injected parameters
- :meth:`diwire.ResolverContext.inject` - a decorator that returns an injected callable wrapper

Basic usage
-----------

Mark injectable parameters using ``Injected[T]``.
All other parameters remain caller-provided.

See the runnable scripts in :doc:`/howto/examples/function-injection` (Injected marker section).

Decorator style
---------------

``ResolverContext.inject`` supports all decorator forms:

- ``@resolver_context.inject``
- ``@resolver_context.inject()``
- ``@resolver_context.inject(scope=Scope.REQUEST, dependency_registration_policy=True)``
- ``@resolver_context.inject(scope=Scope.REQUEST, auto_open_scope=False)``

Example:

.. code-block:: python

   from diwire import Container, Injected, Scope, resolver_context

   container = Container()


   @resolver_context.inject(scope=Scope.REQUEST)
   def handler(service: Injected["Service"]) -> str:
       return service.run()

Behavior notes
--------------

- ``Injected[...]`` parameters are removed from runtime ``__signature__``
- callers can still override injected values by passing explicit keyword arguments
- by default, the wrapper may enter/exit a scope to satisfy scoped dependencies
- to disable implicit scope opening, set ``auto_open_scope=False``

Generated resolver code passes an internal kwarg (``diwire_resolver``) only for inject-wrapped providers.
This is an internal mechanism; user code should not pass it directly unless integrating at a low level.
One exception is ``Container(..., use_resolver_context=False)`` mode: unbound
``@resolver_context.inject`` calls must pass ``diwire_resolver=...`` explicitly
(or run under another bound resolver context).

ContextVar pattern for request values
-------------------------------------

For request-local values, prefer ``contextvars.ContextVar`` and register a normal provider
that reads ``ContextVar.get()``.

.. code-block:: python

   from contextvars import ContextVar

   from diwire import Container, Injected, Scope, resolver_context

   current_user_id_var: ContextVar[int] = ContextVar("current_user_id", default=0)


   def read_current_user_id() -> int:
       return current_user_id_var.get()


   container = Container()
   container.add_factory(read_current_user_id, provides=int, scope=Scope.REQUEST)


   @resolver_context.inject(scope=Scope.REQUEST)
   def handler(user_id: Injected[int]) -> int:
       return user_id


   with container.enter_scope(Scope.REQUEST) as request_scope:
       token = current_user_id_var.set(7)
       try:
           print(handler(diwire_resolver=request_scope))
       finally:
           current_user_id_var.reset(token)

Auto-open scopes (default)
--------------------------

Injected callables may open scopes automatically. With ``auto_open_scope=True`` (default), the
wrapper:

- opens a target scope only when entering a deeper scope is needed and valid
- reuses the current resolver when the target scope is already open (no extra scope entry)
- reuses the current resolver when it is already deeper than the target scope

.. code-block:: python

   from contextvars import ContextVar

   from diwire import Container, Injected, Lifetime, Scope, resolver_context

   class RequestService:
       pass

   current_value_var: ContextVar[int] = ContextVar("current_value", default=0)


   def read_current_value() -> int:
       return current_value_var.get()


   container = Container()
   container.add(
       RequestService,
       provides=RequestService,
       scope=Scope.REQUEST,
       lifetime=Lifetime.SCOPED,
   )
   container.add_factory(read_current_value, provides=int, scope=Scope.SESSION)

   @resolver_context.inject(scope=Scope.REQUEST)
   def use_request_scope(service: Injected[RequestService]) -> RequestService:
       return service

   @resolver_context.inject(scope=Scope.SESSION)
   def read_value(value: Injected[int]) -> int:
       return value

   with container.enter_scope(Scope.REQUEST) as request_scope:
       service = use_request_scope(diwire_resolver=request_scope)

   with container.enter_scope(Scope.SESSION) as session_scope:
       with session_scope.enter_scope(Scope.REQUEST) as request_scope:
           token = current_value_var.set(22)
           try:
               value = read_value(diwire_resolver=request_scope)
           finally:
               current_value_var.reset(token)

Naming note
-----------

The API name is ``inject``. Considered alternatives were ``wire``, ``autowire``, ``inject_call``, and ``inject_params``.

For framework integration (FastAPI/Starlette), also see :doc:`resolver-context` and :doc:`../howto/web/fastapi`.
