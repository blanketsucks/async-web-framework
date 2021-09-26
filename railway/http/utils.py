"""
MIT License

Copyright (c) 2021 blanketsucks

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
import socket
from typing import Generic, Any, Coroutine, TypeVar, Optional
import asyncio

from .errors import InvalidHost

T = TypeVar('T')

class AsyncContextManager(Generic[T]):
    def __init__(self, coroutine: Coroutine[Any, Any, T]) -> None:
        self.coro = coroutine

    def __await__(self):
        return self.coro.__await__()

    async def __aenter__(self) -> T:
        self._resp = await self.coro
        return self._resp

    async def __aexit__(self, *args: Any):
        from .hooker import Websocket

        if isinstance(self._resp, Websocket):
            if not self._resp.is_closed():
                await self._resp.close(b'')
        else:

            if not self._resp._hooker.closed:
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