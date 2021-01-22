import asyncio


class BaseConnection:
    def __init__(self, loop: asyncio.AbstractEventLoop=None, *, app=None) -> None:
        self.loop = loop or asyncio.get_event_loop()
        self.app = app

        self._connection = None

    @property
    def connection(self):
        return self._connection

    async def connect(self):
        raise NotImplementedError

    async def close(self):
        raise NotImplementedError