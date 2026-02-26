import uvicorn
from fastapi import FastAPI
from starlette.websockets import WebSocket

from diwire import Container, Injected, Scope, resolver_context
from diwire.integrations.fastapi import RequestContextMiddleware, add_request_context
from tests.e2e.fastapi.setup.config import FastAPIE2ESettings
from tests.e2e.fastapi.setup.services import (
    CMService,
    RequestBasedService,
    RequestWithCustomStateService,
    WebSocketBasedService,
)

app = FastAPI()
app.add_middleware(RequestContextMiddleware)


@app.get("/services/request-based")
@resolver_context.inject(scope=Scope.REQUEST)
async def request_based_service(service: Injected[RequestBasedService]) -> str:
    return service.work()


@app.get("/services/request-based-with-custom-state")
@resolver_context.inject(scope=Scope.REQUEST)
async def request_based_service_with_custom_state(
    service: Injected[RequestWithCustomStateService],
) -> str:
    return service.work()


@app.websocket("/services/request-based-with-custom-state")
@resolver_context.inject(scope=Scope.SESSION)
async def websocket_request_based_service_with_custom_state(
    ws: WebSocket,
    service: Injected[WebSocketBasedService],
) -> None:
    await ws.accept()
    while True:
        _data = await ws.receive_text()
        await ws.send_text(service.work())


@app.get("/services/cm-service")
@resolver_context.inject(scope=Scope.REQUEST)
async def cm_service(service: Injected[CMService]) -> str:
    return service.work()


def main() -> None:
    container = Container()
    add_request_context(container)
    container.add_context_manager(CMService, scope=Scope.REQUEST)

    settings = container.resolve(FastAPIE2ESettings)
    uvicorn.run(app, host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
