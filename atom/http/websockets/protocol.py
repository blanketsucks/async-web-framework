
import asyncio
from atom.http.abc import Protocol

class WebsocketProtocol(Protocol):
    def __init__(self, client) -> None:
        super().__init__(client)

        self.handshake: asyncio.Future[bytes] = self.loop.create_future()
        self.queue: asyncio.Queue[bytes] = asyncio.Queue()

    async def push(self, data: bytes):
        return await self.queue.put(data)

    async def read(self):
        return await self.queue.get()

    async def wait_for_handshake(self):
        return await self.handshake

    async def wait(self):
        waiter = getattr(self, 'received', None)

        if not waiter:
            return await self.loop.create_future()

        return await waiter

    def data_received(self, data: bytes) -> None:
        if not self.handshake.done():
            return self.handshake.set_result(data)

        self.received = self.create_task(self.push())