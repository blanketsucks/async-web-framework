import asyncpg
import asyncio

from .errors import NoConnections

class PostgresConnection:
    def __init__(self, loop: asyncio.AbstractEventLoop=None) -> None:
        self.loop = loop
        self._connection = None

    @property
    def connection(self):
        return self._connection

    async def connect(self, dsn=None, *, host=None, port=None, user=None, password=None, passfile=None, database=None, **kwargs):
        conn = await asyncpg.create_pool(dsn, host=host, port=port, user=user,
                                        password=password, passfile=passfile,
                                        database=database, loop=self.loop, **kwargs
                                        )
        self._connection = conn
        return conn

    async def create_table(self, name: str):
        pass

    async def fetch(self, table: str):
        pass

    async def execute(self, query: str, *args, *, timeout: float=None):
        res = await self._connection.execute(query, *args, timeout=timeout)
        return res

    async def close(self):
        if not self._connection:
            raise NoConnections('No connections found.')

        await self._connection.close()

