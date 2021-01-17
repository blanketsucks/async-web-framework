
from .request import Request
from .ext.extensions import Resource, Extension
from .error import HTTPException, ExtensionLoadError
from .server import Server
from .router import Route, URLRouter
from .response import Response
from .helper import format_exception
from .ext.tasks import Task

import asyncio
import json
import functools
import inspect
import typing
import importlib


def make_server(app):
    cls = Server(app.loop, app=app, handler=app._handler)
    return cls

class Application:
    """
    
    ## Listeners order

    `on_startup` -> `on_connection_made` -> `on_request` -> `on_socket_receive` -> `on_connection_lost` -> `on_shutdown`
    
    """
    def __init__(self, *, loop: asyncio.AbstractEventLoop=None) -> None:
        self.loop = loop or asyncio.get_event_loop()

        self._router = URLRouter()

        self._middlewares = []
        self._tasks = []

        self._listeners = {}
        self._resources = {}
        self._extensions = {}

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
    def resources(self):
        return self._resources

    @property
    def extensions(self):
        return self._extensions

    @property
    def routes(self):
        return self._router._routes

    @property
    def tasks(self):
        return self._tasks

    def listen(self, name: str=None):
        def decorator(func):
            return self.add_listener(func, name)
        return decorator

    def route(self, path: str, method: str):
        def decorator(func):
            route = Route(path, method, func)
            self.add_route(route)

            return route
        return decorator

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

    def resource(self, path: str):
        def decorator(cls):
            return self.add_resource(cls, path)
        return decorator

    def middleware(self, func):
        return self.add_middleware(func)

    def add_resource(self, cls, path: str):
        if not issubclass(cls, Resource):
            raise RuntimeError('Expected Resource but got {0!r} instead.'.format(cls.__name__))
        
        res = cls(self, path)
        res._unpack()

        self._resources[res.__class__.__name__] = res
        return res

    def add_middleware(self, middleware):
        if not inspect.iscoroutinefunction(middleware):
            raise RuntimeError('All middlewares must be async')

        self._middlewares.append(middleware)
        return middleware

    def add_route(self, route: Route):
        if not inspect.iscoroutinefunction(route.coro):
            raise RuntimeError('All routes must be async')

        self._router.add_route(route)

    def add_listener(self, f, name: str=None):
        if not inspect.iscoroutinefunction(f):
            raise RuntimeError('All listeners must be async')

        actual = f.__name__ if name is None else name
        self._listeners[actual] = f

        return f

    def load_extension(self, filepath: str):
        module = importlib.import_module(filepath)

        try:
            load = getattr(module, 'load')
        except AttributeError:
            raise ExtensionLoadError('Missing load function.')

        load(self)
    
    def add_extension(self, extension):
        if not isinstance(extension, Extension):
            raise ValueError('Extension must inherit from Extension')

        ext = extension._unpack()
        self._extensions[ext.__class__.__name__] = ext

        return ext

    async def dispatch(self, name: str, *args, **kwargs):
        try:
            listener = self._listeners[name]
        except KeyError:
            return

        return await listener(*args, **kwargs)

    async def start(self, host: str=None, *, port: int=None):
        if not host:
            host = '127.0.0.1'

        if not port:
            port = 8080

        serv = make_server(self)
        server: asyncio.AbstractServer = await self.loop.create_server(lambda: serv, host=host, port=port)

        await self.dispatch('on_startup')

        try:
            print('[HTTP]: Server running at http://{0}:{1}/'.format(host, port))
            await server.serve_forever()

        except KeyboardInterrupt:
            await self.dispatch('on_shutdown')
            server.close()

            await server.wait_closed()
            self.loop.stop()

    def run(self, host: str=None, *, port: int=None):
        if not host:
            host = '127.0.0.1'

        if not port:
            port = 8080

        serv = make_server(self)

        server = self.loop.run_until_complete(
            self.loop.create_server(lambda: serv, host=host, port=port)
        )
        self.loop.run_until_complete(self.dispatch('on_startup'))

        try:
            print('[HTTP]: Server running at http://{0}:{1}/'.format(host, port))
            self.loop.run_until_complete(server.serve_forever())
        except KeyboardInterrupt:
            self.loop.run_until_complete(self.dispatch('on_shutdown'))
            server.close()
            
            self.loop.run_until_complete(server.wait_closed())
            self.loop.stop()

    async def _handler(self, request, response_writer):
        try:

            handler = self._router.resolve(request)
            request.args = {}

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

    # Editing any of the following methods will do nothing since they're here as a refrence for listeners

    async def on_startup(self): ...

    async def on_shutdown(self): ...

    async def on_error(self, exc: typing.Union[HTTPException, Exception]): ...

    async def on_request(self, request: Request): ...

    async def on_socket_receive(self, data: bytes): ...

    async def on_connection_made(self, transport: asyncio.BaseTransport): ...

    async def on_connection_lost(self, exc: typing.Optional[Exception]): ...
