import asyncio
import typing

from .errors import NoConnections
from ..application import Application
from ..restful import App

class BaseConnection:
    def __init__(self, loop: asyncio.AbstractEventLoop=None, *, app: typing.Union[Application, App]=None) -> None:
        self.loop = loop or asyncio.get_event_loop()
        self.app = app

        self._connection = None

    @property
    def connection(self):
        return self._connection

    async def connect(self):
        raise NotImplementedError

    async def close(self):
        if not self._connection:
            raise NoConnections('No connections have been made.')

        if self.app:
            await self.app.dispatch('on_database_close')

        await self._connection.close()