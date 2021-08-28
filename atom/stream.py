from typing import List, Optional, Union, Any
import asyncio

from . import compat

class StreamWriter:
    def __init__(self, transport: asyncio.Transport) -> None:
        self._transport = transport
        self._waiter: 'Optional[asyncio.Future[None]]' = None

    async def _wait_for_drain(self):
        if self._waiter is None:
            return

        try:
            await self._waiter
        finally:
            self._waiter = None

    async def write(self, data: Union[bytearray, bytes]) -> None:
        self._transport.write(data)
        await self._wait_for_drain()

    async def writelines(self, data: List[Union[bytearray, bytes]]) -> None:
        self._transport.writelines(data)
        await self._wait_for_drain()

    def get_extra_info(self, name: str, default: Any=None) -> Any:
        return self._transport.get_extra_info(name, default)

    def close(self):
        self._transport.close()

class StreamReader:
    def __init__(self) -> None:
        self.buffer = bytearray()
        self.loop = compat.get_running_loop()

        self._waiter = None

    async def _wait_for_data(self, timeout: Optional[float]=None):
        self._waiter = self.loop.create_future()

        try:
            await asyncio.wait_for(self._waiter, timeout)
        finally:
            self._waiter = None

    def feed_data(self, data: Union[bytearray, bytes]) -> None:
        self.buffer.extend(data)

        if self._waiter:
            self._waiter.set_result(None)

    def feed_eof(self):
        return

    async def read(self, nbytes: Optional[int]=None, *, timeout: Optional[float]=None):
        if not self.buffer:
            await self._wait_for_data(timeout=timeout)

        if not nbytes:
            data = self.buffer
            self.buffer = bytearray()

            return bytes(data)

        if nbytes > len(self.buffer):
            await self._wait_for_data(timeout=timeout)

        data = self.buffer[:nbytes]
        self.buffer = self.buffer[nbytes:]

        return bytes(data)