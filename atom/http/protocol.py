from __future__ import annotations
import asyncio
import typing

from .abc import Protocol

if typing.TYPE_CHECKING:
    from .client import HTTPSession

class HTTPProtocol(Protocol):
    def __init__(self, client: HTTPSession) -> None:
        self.client = client
        self.queue: asyncio.Queue[bytes] = asyncio.Queue()
        self.received = self.loop.create_future()

    def __call__(self):
        return self

    async def push(self, data: bytes):
        await self.queue.put(data)

    async def read(self):
        return await self.queue.get()

    async def wait(self):
        await self.received
        await self.read_task

    def data_received(self, data: bytes) -> None:
        if not self.received.done():
            self.received.set_result(None)
            
        self.read_task = self.client.loop.create_task(self.push(data))