from __future__ import annotations

import pytest

pytest.importorskip("flask")

from flask import Flask, Request

import diwire._internal.integrations.flask as flask_integration
from diwire import Container
from diwire.exceptions import DIWireIntegrationError


def test_get_request_raises_when_context_is_missing() -> None:
    with pytest.raises(DIWireIntegrationError, match="Request context not available"):
        flask_integration.get_request()


def test_get_request_returns_current_flask_request() -> None:
    app = Flask(__name__)
    with app.test_request_context("/middleware/context"):
        resolved_request = flask_integration.get_request()
        assert resolved_request.path == "/middleware/context"


def test_add_request_context_registers_factory_for_container_resolution() -> None:
    container = Container()
    flask_integration.add_request_context(container)

    app = Flask(__name__)
    with app.test_request_context("/container/request"):
        resolved_request = container.resolve(Request)
        assert resolved_request.path == "/container/request"
