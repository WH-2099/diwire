from __future__ import annotations

import pytest

from diwire import AsyncProvider, Container, Injected, Lifetime

pytest_plugins = ["diwire.integrations.pytest_plugin"]


class Service:
    pass


class ServiceImpl(Service):
    pass


class UpdatedService(Service):
    pass


@pytest.fixture()
def diwire_container() -> Container:
    container = Container()
    container.add(
        ServiceImpl,
        provides=Service,
        lifetime=Lifetime.SCOPED,
    )
    return container


def test_plugin_injects_parameters(service: Injected[Service]) -> None:
    if not isinstance(service, ServiceImpl):
        msg = "Injected service is not ServiceImpl"
        raise TypeError(msg)


@pytest.mark.asyncio
async def test_async_provider_sees_test_override(
    diwire_container: Container,
    service_provider: Injected[AsyncProvider[Service]],
) -> None:
    before = await service_provider()

    diwire_container.add_instance(UpdatedService(), provides=Service)
    after = await service_provider()

    if not isinstance(before, ServiceImpl):
        msg = "Injected async provider did not use original Service"
        raise TypeError(msg)

    if not isinstance(after, UpdatedService):
        msg = "Injected async provider did not use updated Service"
        raise TypeError(msg)
