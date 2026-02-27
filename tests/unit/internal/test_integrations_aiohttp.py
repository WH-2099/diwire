from __future__ import annotations

import pytest

pytest.importorskip("aiohttp")

from aiohttp import web
from aiohttp.test_utils import make_mocked_request

import diwire._internal.integrations.aiohttp as aiohttp_integration
from diwire import Container
from diwire.exceptions import DIWireIntegrationError


def test_get_request_raises_when_context_is_missing() -> None:
    with pytest.raises(DIWireIntegrationError, match="Request context not available"):
        aiohttp_integration.get_request()


@pytest.mark.asyncio
async def test_request_context_middleware_sets_context_for_handler() -> None:
    request = make_mocked_request("GET", "/middleware/context")

    async def handler(current_request: web.Request) -> web.StreamResponse:
        resolved_request = aiohttp_integration.get_request()
        assert resolved_request is current_request
        return web.Response(text="ok")

    response = await aiohttp_integration.request_context_middleware(request, handler)

    assert response.status == 200


@pytest.mark.asyncio
async def test_request_context_middleware_resets_context_after_success() -> None:
    request = make_mocked_request("GET", "/middleware/success")

    async def handler(_request: web.Request) -> web.StreamResponse:
        assert aiohttp_integration.get_request().path == "/middleware/success"
        return web.Response(text="ok")

    await aiohttp_integration.request_context_middleware(request, handler)

    with pytest.raises(DIWireIntegrationError, match="Request context not available"):
        aiohttp_integration.get_request()


@pytest.mark.asyncio
async def test_request_context_middleware_resets_context_after_exception() -> None:
    request = make_mocked_request("GET", "/middleware/error")

    async def handler(_request: web.Request) -> web.StreamResponse:
        assert aiohttp_integration.get_request().path == "/middleware/error"
        msg = "handler failed"
        raise RuntimeError(msg)

    with pytest.raises(RuntimeError, match="handler failed"):
        await aiohttp_integration.request_context_middleware(request, handler)

    with pytest.raises(DIWireIntegrationError, match="Request context not available"):
        aiohttp_integration.get_request()


def test_add_request_context_registers_factory_for_container_resolution() -> None:
    container = Container()
    aiohttp_integration.add_request_context(container)

    request = make_mocked_request("GET", "/container/request")
    token = aiohttp_integration._request_context.set(request)
    try:
        resolved_request = container.resolve(web.Request)
        assert resolved_request is request
    finally:
        aiohttp_integration._request_context.reset(token)
