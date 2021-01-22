import asyncpg
import asyncio
import typing

from .errors import NoConnections
from .base import BaseConnection

class PostgresConnection(BaseConnection):

    async def connect(self, dsn=None, *, host=None, port=None, user=None,
                    password=None, passfile=None, database=None, **kwargs) -> asyncpg.pool.Pool:

        conn = await asyncpg.create_pool(dsn, host=host, port=port, user=user,
                                        password=password, passfile=passfile,
                                        database=database, loop=self.loop, **kwargs
                                        ) 
        if self.app:
            await self.app.dispatch('on_database_connect', conn)

        self._connection = conn
        return conn

    async def create_table(self, query: str, *args) -> str:
        res = await self._connection.execute(query, *args)
        return res

    async def fetch_all(self, query: str, *args) -> typing.List[asyncpg.Record]:
        res = await self._connection.fetch(query, *args)
        return res

    async def fetch_one(self, query: str, *args, column=0):
        res = await self._connection.fetchval(query, *args, column=column)
        return res

    async def fetch_row(self, query: str, *args):
        res = await self._connection.fetchrow(query, *args)
        return res

    async def execute(self, query: str, *args, timeout: float=None):
        res = await self._connection.execute(query, *args, timeout=timeout)
        return res

    async def close(self):
        if not self._connection:
            raise NoConnections('No connections found.')

        if self.app:
            await self.app.dispatch('on_database_close')

        await self._connection.close()
