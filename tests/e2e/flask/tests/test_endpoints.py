from __future__ import annotations

import os
from collections.abc import AsyncIterator

import httpx
import pytest

_BASE_HTTP_URL_ENV = "FLASK_E2E_BASE_HTTP_URL"

if os.getenv(_BASE_HTTP_URL_ENV) is None:
    pytest.skip(
        f"{_BASE_HTTP_URL_ENV} is not set; skipping docker-compose Flask e2e tests.",
        allow_module_level=True,
    )


def _base_http_url() -> str:
    return os.getenv(_BASE_HTTP_URL_ENV, "http://api:8240").rstrip("/")


@pytest.fixture()
async def http_client() -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(base_url=_base_http_url(), timeout=10.0) as client:
        yield client


@pytest.mark.asyncio
async def test_health_returns_ok(http_client: httpx.AsyncClient) -> None:
    response = await http_client.get("/health")
    assert response.status_code == 200
    assert response.text == "OK"


@pytest.mark.asyncio
async def test_request_based_returns_request_path(http_client: httpx.AsyncClient) -> None:
    response = await http_client.get("/services/request-based")
    assert response.status_code == 200
    assert response.text == "Request path: /services/request-based"


@pytest.mark.asyncio
async def test_context_manager_service_validates_request_scope_cleanup_path(
    http_client: httpx.AsyncClient,
) -> None:
    response = await http_client.get("/services/cm-service")
    assert response.status_code == 200
    assert response.text == "CMService working"

    cleanup_response = await http_client.get("/services/cm-service/cleanup")
    assert cleanup_response.status_code == 200
    assert cleanup_response.text == "Cleanup path: /services/cm-service"
