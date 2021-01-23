
from .error import HTTPException
from .request import Request
from .objects import Listener


import inspect
import typing
import asyncpg
import asyncio
import aioredis
import aiosqlite

class ListenersHandler:
    def __init__(self) -> None:
        self.listeners: typing.Dict[str, typing.List[typing.Coroutine]] = {}

    def add_listener(self, f: typing.Coroutine, name: str=None) -> Listener:
        actual = f.__name__ if name is None else name

        if actual in self.listeners:
            self.listeners[actual].append(f)
        else:
            self.listeners[actual] = [f]
    
        return Listener(f, actual)

    def remove_listener(self, func: typing.Coroutine=None, name: str=None):
        if not func:
            if name:
                coros = self.listeners.pop(name)
                return coros

            raise TypeError('Only the function or the name can be None, not both.')

        self.listeners[name].remove(func)

    # Editing any of the following methods will do nothing since they're here as a refrence for listeners

    async def on_startup(self, host: str, port: int): ...

    async def on_shutdown(self): ...

    async def on_error(self, exc: typing.Union[HTTPException, Exception]): ...

    async def on_request(self, request: Request): ...

    async def on_socket_receive(self, data: bytes): ...

    async def on_connection_made(self, transport: asyncio.BaseTransport): ...

    async def on_connection_lost(self, exc: typing.Optional[Exception]): ...

    async def on_database_connect(self, connection: typing.Union[asyncpg.pool.Pool, aioredis.Redis, aiosqlite.Connection]): ...

    async def on_database_close(self): ...
