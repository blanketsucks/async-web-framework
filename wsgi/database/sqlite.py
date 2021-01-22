import aiosqlite
import asyncio
import pathlib
import typing

if typing.TYPE_CHECKING:
    from .. import Application
    from ..restful import App

class SQLiteConnection:
    def __init__(self, loop: asyncio.AbstractEventLoop=None, *, app: typing.Union['App', 'Application']=None) -> None:
        self.loop = loop or asyncio.get_event_loop()
        self.app = app

    async def connect(self, database: typing.Union[str, pathlib.Path], **kwargs):
        connection = await aiosqlite.connect(database, loop=self.loop, **kwargs)

        if self.app:
            await self.app.dispatch('on_database_connect', connection)

        self._connection = connection
        return connection

    async def execute(self, *args, **kwargs):
        cur = await self._connection.execute(*args, **kwargs)
        return cur

    async def execute_many(self, *args, **kwargs):
        cur = await self._connection.executemany(*args, **kwargs)
        return cur

    async def fetch_all(self, *args, **kwargs):
        cur = await self._connection.execute_fetchall(*args, **kwargs)
        return cur

    async def cursor(self, *args, **kwargs):
        cursor = await self._connection.cursor(*args, **kwargs)
        return cursor

    async def close(self):
        await self._connection.close()