from __future__ import annotations

from typing import Any, Coroutine, TYPE_CHECKING, Generator
import asyncio

if TYPE_CHECKING:
    from .response import HTTPResponse
    from subway.websockets import ClientWebSocket

class RequestContextManager:
    def __init__(self, coroutine: Coroutine[Any, Any, HTTPResponse]) -> None:
        self.coro = coroutine
        self.response: HTTPResponse = None  # type: ignore

    def __await__(self) -> Generator[Any, Any, HTTPResponse]:
        return self.coro.__await__()

    async def __aenter__(self) -> HTTPResponse:
        self.response = resp = await self.coro
        return resp

    async def __aexit__(self, *args: Any):
        if not self.response.hooker.closed:
            await self.response.close()

class WebSocketContextManager:
    def __init__(self, coroutine: Coroutine[Any, Any, ClientWebSocket]) -> None:
        self.coro = coroutine
        self.websocket: ClientWebSocket = None  # type: ignore

    def __await__(self):
        return self.coro.__await__()

    async def __aenter__(self) -> ClientWebSocket:
        self.websocket = ws = await self.coro
        return ws

    async def __aexit__(self, *args: Any):
        await asyncio.sleep(0)

        if not self.websocket.is_closed():
            await self.websocket.close()
