import socket
from typing import Generic, Any, Coroutine, Tuple, TypeVar, Optional
import asyncio

from .errors import InvalidHost

T = TypeVar('T')

class AsyncContextManager(Generic[T]):
    def __init__(self, coroutine: Coroutine[Any, Any, T]) -> None:
        self.coro = coroutine

    def __await__(self):
        return self.coro.__await__()

    async def __aenter__(self):
        self._resp = await self.coro
        return self._resp

    async def __aexit__(self, *args: Any):
        from .hooker import Websocket

        if isinstance(self._resp, Websocket):
            await self._resp.close(b'')
        else:
            await self._resp._hooker.close() # type: ignore
            
        return self

class _AsyncIterator(Generic[T]):
    def __init__(self, coroutine: Coroutine[Any, Any, Any]) -> None:
        self.coroutine = coroutine
        self.future = asyncio.ensure_future(self.coroutine)

        self.index = 0

    def __await__(self):
        return self.future.__await__()

    def __aiter__(self):
        return self

    async def __anext__(self) -> T:
        if not self.future.done():
            self.results = list(await self.future)

        try:
            ret = self.results.pop(self.index)
            return ret
        except IndexError:
            raise StopAsyncIteration
        else:
            self.index += 1

class AsyncIterator(_AsyncIterator[T]):
    def __init__(self, coroutine: Coroutine[Any, Any, Any], host: Optional[str]) -> None:
        super().__init__(coroutine)
        self.host = host

    async def __anext__(self):
        try:
            return await super().__anext__()
        except socket.gaierror:
            raise InvalidHost(self.host)