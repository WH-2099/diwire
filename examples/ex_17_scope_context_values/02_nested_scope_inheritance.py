"""Focused example: nested scope work can use ContextVar override/reset tokens."""

from __future__ import annotations

from contextvars import ContextVar

from diwire import Container, Lifetime, Scope

request_id_var: ContextVar[int] = ContextVar("request_id", default=-1)
tenant_var: ContextVar[str] = ContextVar("tenant", default="unset")


def read_request_id() -> int:
    return request_id_var.get()


def read_tenant() -> str:
    return tenant_var.get()


def main() -> None:
    container = Container()
    container.add_factory(
        read_request_id,
        provides=int,
        scope=Scope.REQUEST,
        lifetime=Lifetime.TRANSIENT,
    )
    container.add_factory(
        read_tenant,
        provides=str,
        scope=Scope.REQUEST,
        lifetime=Lifetime.TRANSIENT,
    )

    with container.enter_scope(Scope.REQUEST) as request_scope:
        request_id_token = request_id_var.set(1)
        tenant_token = tenant_var.set("parent")
        try:
            with request_scope.enter_scope(Scope.ACTION) as action_scope:
                inherited_value = action_scope.resolve(int)

                override_token = request_id_var.set(2)
                try:
                    with action_scope.enter_scope(Scope.STEP) as step_scope:
                        overridden_value = step_scope.resolve(int)
                        inherited_parent_key = step_scope.resolve(str)
                finally:
                    request_id_var.reset(override_token)
        finally:
            tenant_var.reset(tenant_token)
            request_id_var.reset(request_id_token)

    print(f"action_inherits_parent={inherited_value}")  # => action_inherits_parent=1
    print(f"step_overrides_parent={overridden_value}")  # => step_overrides_parent=2
    print(
        f"step_inherits_other_parent_key={inherited_parent_key}"
    )  # => step_inherits_other_parent_key=parent


if __name__ == "__main__":
    main()
