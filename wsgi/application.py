

from .request import Request
from .error import HTTPException
from .server import Server
from .router import URLRouter
from .response import Response
from .helpers import format_exception
from .tasks import Task
from .settings import Settings

import asyncio
import json
import functools
import inspect
import typing

import asyncpg
import aioredis
import aiosqlite

class Route:
    def __init__(self, path: str, method: str, coro: typing.Coroutine) -> None:
        self._path = path
        self._method = method
        self._coro = coro

    @property
    def path(self):
        return self._path

    @property
    def method(self):
        return self._method

    @property
    def coro(self):
        return self._coro

class Middleware:
    def __init__(self, coro: typing.Coroutine) -> None:
        self._coro = coro

    @property
    def coro(self):
        return self._coro

class Listener:
    def __init__(self, coro: typing.Coroutine, name: str=None) -> None:
        self._event = name
        self._coro = coro

    @property
    def event(self):
        return self._event

    @property
    def coro(self):
        return self._coro


class Application:
    """
    
    ## Listeners order

    `on_startup` -> `on_connection_made` -> `on_request` -> `on_socket_receive` -> `on_connection_lost` -> `on_shutdown`
    
    """
    def __init__(self, routes: typing.List[Route]=None,
                listeners: typing.List[Listener]=None,
                middlewares: typing.List[Middleware]=None, *,
                loop: asyncio.AbstractEventLoop=None) -> None:

        self.loop = loop or asyncio.get_event_loop()
        self.settings = Settings()

        self._router = URLRouter()

        self._middlewares: typing.List[typing.Coroutine] = []
        self._tasks: typing.List[Task] = []
        self._listeners: typing.Dict[str, typing.List[typing.Coroutine]] = {}

        self._load_from_arguments(routes=routes, listeners=listeners, middlewares=middlewares)

    def make_server(self, cls=Server):
        res = cls(self.loop, app=self, handler=self._handler)
        return res

    @property
    def router(self):
        return self._router

    @property
    def middlewares(self):
        return self._middlewares

    @property
    def listeners(self):
        return self._listeners

    @property
    def routes(self):
        return self._router._routes

    @property
    def tasks(self):
        return self._tasks

    def task(self, *, seconds=0, minutes=0, hours=0, count=None, loop=None):
        def wrapper(func):
            cls = Task(
                func,
                seconds,
                minutes,
                hours,
                count,
                loop
            )

            self._tasks.append(cls)
            return cls
        return wrapper

    def _load_from_arguments(self, routes: typing.List[Route]=None, listeners: typing.List[Listener]=None, 
                            middlewares: typing.List[Middleware]=None):

        if routes:
            for route in routes:
                self.add_route(route)

        if listeners:
            for listener in listeners:
                coro = listener.coro
                name = listener.event

                self.add_listener(coro, name)

        if middlewares:
            for middleware in middlewares:
                coro = middleware.coro
                self.add_middleware(coro)

    # Running the app

    async def start(self, host: str=None, *, port: int=None):
        for task in self._tasks:
            task.start()

        if not host:
            host = '127.0.0.1'

        if not port:
            port = 8080

        serv = self.make_server()
        server: asyncio.AbstractServer = await self.loop.create_server(lambda: serv, host=host, port=port)

        await self.dispatch('on_startup', host, port)

        try:
            await server.serve_forever()
        except KeyboardInterrupt:
            await self.dispatch('on_shutdown')
            server.close()

            await server.wait_closed()
            self.loop.stop()

    def run(self, host: str=None, *, port: int=None):
        for task in self._tasks:
            task.start()

        if not host:
            host = '127.0.0.1'

        if not port:
            port = 8080

        serv = self.make_server()

        server = self.loop.run_until_complete(
            self.loop.create_server(lambda: serv, host=host, port=port)
        )
        self.loop.run_until_complete(self.dispatch('on_startup', host, port))

        try:
            self.loop.run_until_complete(server.serve_forever())
        except KeyboardInterrupt:
            self.loop.run_until_complete(self.dispatch('on_shutdown'))
            server.close()
            
            self.loop.run_until_complete(server.wait_closed())
            self.loop.stop()

    # Route handler 

    async def _handler(self, request: Request, response_writer):
        try:
            handler = self._router.resolve(request)

            if len(self._middlewares) != 0:
                for middleware in self._middlewares:
                    handler = functools.partial(middleware, handler=handler)
                
            resp = await handler(request)

            if isinstance(resp, dict) or isinstance(resp, list):
                data = json.dumps(resp)
                resp = Response(data, content_type='application/json')

            if isinstance(resp, str):
                resp = Response(resp)

        except HTTPException as exc:
            await self.dispatch('on_error', exc)
            resp = exc

        except Exception as exc:
            await self.dispatch('on_error', exc)
            resp = format_exception(exc)

        response_writer(resp)

    # Routing

    def add_route(self, route: Route):
        if not inspect.iscoroutinefunction(route.coro):
            raise RuntimeError('All routes must be async')

        self._router.add_route(route)
        return route

    def remove_route(self, path: str, method: str):
        return self._router.remove_route(method, path)

    def route(self, path: str, method: str):
        def decorator(func: typing.Coroutine):
            route = Route(path, method, func)
            return self.add_route(route)

        return decorator

    def get(self, path: str):
        def decorator(func: typing.Coroutine):
            route = Route(path, 'GET', func)
            self.add_route(route)

            return route
        return decorator

    def put(self, path: str):
        def decorator(func: typing.Coroutine):
            route = Route(path, 'PUT', func)
            self.add_route(route)

            return route
        return decorator

    def post(self, path: str):
        def decorator(func: typing.Coroutine):
            route = Route(path, 'POST', func)
            self.add_route(route)

            return route
        return decorator

    def delete(self, path: str):
        def decorator(func: typing.Coroutine):
            route = Route(path, 'DELETE', func)
            self.add_route(route)

            return route
        return decorator

    # Listeners

    def add_listener(self, f: typing.Coroutine, name: str=None) -> Listener:
        if not inspect.iscoroutinefunction(f):
            raise RuntimeError('All listeners must be async')

        actual = f.__name__ if name is None else name

        if actual in self._listeners:
            self._listeners[actual].append(f)
        else:
            self._listeners[actual] = [f]
    
        return Listener(f, actual)


    def remove_listener(self, func: typing.Coroutine=None, name: str=None):
        if not func:
            if name:
                coros = self._listeners.pop(name)
                return coros

            raise TypeError('Only the function or the name can be None, not both.')

        self._listeners[name].remove(func)

    def listen(self, name: str=None):
        def decorator(func: typing.Coroutine):
            return self.add_listener(func, name)
        return decorator

    async def dispatch(self, name: str, *args, **kwargs):
        try:
            listeners = self._listeners[name]
        except KeyError:
            return
        
        for listener in listeners:
            await listener(*args, **kwargs)

        return listeners

    # Middlewares

    def middleware(self):
        def wrapper(func: typing.Coroutine):
            return self.add_middleware(func)
        return wrapper

    def add_middleware(self, middleware: typing.Coroutine):
        if not inspect.iscoroutinefunction(middleware):
            raise RuntimeError('All middlewares must be async')

        self._middlewares.append(middleware)
        return Middleware(middleware)

    def remove_middleware(self, middleware: typing.Coroutine) -> typing.Coroutine:
        self._middlewares.remove(middleware)
        return middleware
    
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
