from __future__ import annotations

from flask import Request, has_request_context, request

from diwire import Container, Lifetime
from diwire.exceptions import DIWireIntegrationError


def get_request() -> Request:
    if not has_request_context():
        msg = "Request context not available. Ensure this is called during an active Flask request."
        raise DIWireIntegrationError(msg)
    return request


def add_request_context(container: Container) -> None:
    container.add_factory(
        get_request,
        provides=Request,
        lifetime=Lifetime.TRANSIENT,
    )
