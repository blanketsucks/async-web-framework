from .request import Request
from .errors import *
from .protocol import ApplicationProtocol
from .datastructures import URL
from .router import Router
from . import utils
from .settings import Settings
from .objects import Route, Listener, WebsocketRoute
from .views import HTTPView, WebsocketHTTPView
from .extensions import Extension
from .shards import Shard
from .typings import (
    Routes,
    Listeners,
    Extensions,
    Shards,
    Awaitable
)
from .response import Response, JSONResponse

import inspect
import typing
import datetime
import asyncio
import importlib
import watchgod

def _get_event_loop(loop=None):
    if loop:
        if not isinstance(loop, asyncio.AbstractEventLoop):
            raise TypeError('Invalid argument type for loop argument')

        return loop

    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.get_event_loop()

__all__ = (
    'Application',
)

class Application:
    def __init__(self, routes=None, listeners=None, extensions: Extensions=None,
                shards=None, *, loop=None, url_prefix=None,
                settings_file=None, load_settings_from_env=None):

        routes = routes or []
        listeners = listeners or []
        extensions = extensions or []
        shards = shards or []

        self._ready = asyncio.Event()
        self.loop = _get_event_loop(loop)
        self.url_prefix = url_prefix or ''
        self.settings = Settings(None, False)
        self.router = Router()
        self.views = {}
        self.shards = {}

        if settings_file is True:
            self.settings.from_file(settings_file)

        if load_settings_from_env is True:
            self.settings.from_env_vars()

        self._listeners: typing.Dict[str, typing.List[typing.Callable]] = {}
        self._extensions: typing.Dict[str, Extension] = {}
        self._protocol = ApplicationProtocol(
            app=self,
        )
        self._server = None
        self._database_connection = None
        self._backlog = 5

        self._load_from_arguments(routes, listeners, extensions, shards)

    def __repr__(self) -> str:
        return '<Application>'

    def set_backlog(self, backlog: int):
        if self._server:
            raise ValueError('Can not set backlog once the app has started')

        self._backlog = backlog

    def _load_from_arguments(self, 
                            routes: Routes,
                            listeners: Listeners,
                            extensions: Extensions,
                            shards: Shards):
        
        for route in routes:
            self.add_route(route)

        for listener in listeners:
            coro = listener.coro
            name = listener.event

            self.add_listener(coro, name)

        for ext in extensions:
            self.register_extension(ext)

        for shard in shards:
            self.register_shard(shard)

        return self

    async def _watch_for_changes(self):
        async for changes in watchgod.awatch('.', watcher_cls=watchgod.PythonWatcher):
            for change in changes:
                self.__datetime = datetime.datetime.utcnow().strftime('%Y-%m-%d | %H:%M:%S')
                print(f"[{self.__datetime}]: Detected change in {change[1]}. Reloading.")

                filepath = change[1][2:-3].replace('\\', '.')

                module = importlib.import_module(filepath)
                importlib.reload(module)

    def _convert(self, func, args):
        return_args = []
        params = inspect.signature(func)

        for key, value in params.parameters.items():
            for name, match in args.items():
                if key == name:
                    try:
                        param = value.annotation(match)
                    except ValueError:
                        fut = 'Failed conversion to {0!r} for parameter {1!r}.'.format(value.annotation.__name__, key)
                        raise BadConversion(fut) from None
                    else:
                        return_args.append(param)

        return return_args

    async def _request_handler(self, request: Request, *, websocket):
        resp = None
        try:
            args, route = self.router.resolve(request)

            if getattr(route, '_waiter', None):
                route._waiter.set_result(request)

            # route._extras['params'] = args
            request.route = route

            args = self._convert(route.callback, args)
            if len(route.middlewares) != 0:
                await asyncio.gather(*[middleware(route, request, *args) for middleware in route.middlewares])

            if isinstance(route, WebsocketRoute):
                self.loop.create_task(
                    coro=route(request, websocket)
                )
                return

            resp = await route(request, *args)

            if isinstance(resp, str):
                resp = Response(
                    body=resp, 
                    status=200, 
                    content_type='text/plain'
                )

            if isinstance(resp, (dict, tuple)):
                resp = JSONResponse(
                    body=resp,
                    status=200
                )

        except Exception as exc:
            resp = utils.format_exception(exc)
            self.dispatch('on_error', exc)

        transport = self.get_transport()
        transport.write(resp.encode())

        transport.close()

    async def wait_until_startup(self):
        await self._ready.wait()

    def is_ready(self):
        return self._ready.is_set()

    @property
    def listeners(self):
        return self._listeners

    @property
    def extensions(self):
        return self._extensions

    @property
    def protocol(self):
        return self._protocol

    @protocol.setter
    def protocol(self, value):
        if not isinstance(value, asyncio.Protocol):
            raise ValueError('Expected sockets.Protocol but got {0.__class__.__name__} instead'.format(value))

        self._protocol = value

    def get_transport(self) -> typing.Optional[asyncio.Transport]:
        return getattr(self._protocol, 'transport', None)

    async def start(self,
                    host: str = ...,
                    port: int = ...,
                    *,
                    debug: bool = ...):
        debug = False if debug is ... else debug

        if debug:
            self.loop.create_task(self._watch_for_changes())

        server: asyncio.AbstractServer = await self.loop.create_server(self._protocol, host, port)
        self._server = server

        await server.serve_forever()

    async def close(self):
        server = self._server
        if not server:
            raise ApplicationError('The Application is not running')

        await server.wait_closed()
        server.close()

        self.dispatch('on_shutdown')

    def run(self, *args: typing.Tuple, **kwargs: typing.Mapping):
        return self.loop.run_until_complete(self.start(*args, **kwargs))

    def websocket(self, path: str):
        def decorator(coro: Awaitable) -> WebsocketRoute:
            route = WebsocketRoute(path, 'GET', coro, app=self)
            route.subprotocols = tuple()

            return self.add_route(route)
        return decorator

    def route(self, path: typing.Union[str, URL], method: str):
        def decorator(func: Awaitable) -> Route:
            actual = path

            if isinstance(path, URL):
                actual = path.path

            route = Route(actual, method, func, app=self)
            return self.add_route(route)

        return decorator

    def add_route(self, route: typing.Union[Route, WebsocketRoute]):
        if not isinstance(route, (Route, WebsocketRoute)):
            fmt = 'Expected Route or WebsocketRoute but got {0!r} instead'
            raise RouteRegistrationError(fmt.format(route.__class__.__name__))

        if not inspect.iscoroutinefunction(route.callback):
            raise RouteRegistrationError('Routes must be async.')

        if route in self.router.routes:
            raise RouteRegistrationError('{0!r} is already a route.'.format(route.path))

        if isinstance(route, WebsocketRoute):
            self.router.add_route(route, websocket=True)
            return route

        self.router.add_route(route)
        return route

    def get(self, path: typing.Union[str, URL]):
        def decorator(func: Awaitable) -> Route:
            return self.route(path, 'GET')(func)
        return decorator

    def put(self, path: typing.Union[str, URL]):
        def decorator(func: Awaitable):
            return self.route(path, 'PUT')(func)
        return decorator

    def post(self, path: typing.Union[str, URL]):
        def decorator(func: Awaitable):
            return self.route(path, 'POST')(func)
        return decorator

    def delete(self, path: typing.Union[str, URL]):
        def decorator(func: Awaitable):
            return self.route(path, 'DELETE')(func)
        return decorator

    def head(self, path: typing.Union[str, URL]):
        def decorator(func: Awaitable):
            return self.route(path, 'HEAD')(func)
        return decorator

    def options(self, path: typing.Union[str, URL]):
        def decorator(func: Awaitable):
            return self.route(path, 'OPTIONS')(func)
        return decorator

    def patch(self, path: typing.Union[str, URL]):
        def decorator(func: Awaitable):
            return self.route(path, 'PATCH')(func)
        return decorator

    def remove_route(self, route: typing.Union[Route, WebsocketRoute]):
        self.router.routes.remove(route)
        return route

    # dispatching and listeners

    def add_listener(self, coro: Awaitable, name: str = None):
        if not inspect.iscoroutinefunction(coro):
            raise ListenerRegistrationError('Listeners must be coroutines')

        actual = name if name else coro.__name__

        if not actual in utils.VALID_LISTENERS:
            raise ListenerRegistrationError(f'{actual!r} is not a valid listener')

        if actual in self._listeners.keys():
            self._listeners[actual].append(coro)
            return Listener(coro, actual)

        self._listeners[actual] = [coro]
        return Listener(coro, actual)

    def remove_listener(self, func: Awaitable = None, name: str = None):
        if not func:
            if name:
                self._listeners.pop(name.lower())

            raise TypeError('Only the function or the name can be None, not both.')

        self._listeners[name].remove(func)

    def listen(self, name: str = None):
        def decorator(func: Awaitable):
            return self.add_listener(func, name)

        return decorator

    def dispatch(self, name: str, *args, **kwargs):
        try:
            listeners = self._listeners[name]
        except KeyError:
            return

        for listener in listeners:
            if isinstance(listener, asyncio.Future):
                if len(args) == 0:
                    listener.set_result(None)
                elif len(args) == 1:
                    listener.set_result(args[0])
                else:
                    listener.set_result(args)

                listeners.remove(listener)
                continue
            
            self.loop.create_task(listener(*args, **kwargs))

    def register_shard(self, shard: Shard):
        if not isinstance(shard, Shard):
            fmt = 'Expected Shard but got {0.__class__.__name__} instead'
            raise ShardRegistrationError(fmt.format(shard))

        if shard.name in self.shards:
            raise ShardRegistrationError(f'{shard.name!r} is an already existing shard')

        self.shards[shard.name] = shard
        return shard._unpack(self)

    def register_view(self, view: HTTPView):
        if not isinstance(view, HTTPView):
            raise ViewRegistrationError('Expected HTTPView but got {0!r} instead.'.format(view.__class__.__name__))

        for route in view.as_routes(app=self):
            self.add_route(route)

        self.views[view.__url_route__] = view
        return view

    def register_websocket_view(self, view: WebsocketHTTPView):
        if not isinstance(view, WebsocketHTTPView):
            raise ViewRegistrationError(
                'Expected WebsocketHTTPView but got {0!r} instead.'.format(view.__class__.__name__))

        for route in view.as_routes(app=self):
            self.add_route(route, websocket=True)

        self.views[view.__url_route__] = view
        return view

    def view(self, path: str):
        def decorator(cls):
            if cls.__url_route__ == '':
                cls.__url_route__ = path

            view = cls()
            return self.register_view(view)
        return decorator

    def middleware(self, route: Route):
        def wrapper(func: Awaitable):
            return route.add_middleware(func)
        return wrapper

    def register_extension(self, filepath: str) -> typing.List[Extension]:
        try:
            module = importlib.import_module(filepath)
        except Exception as exc:
            raise ExtensionLoadError('Failed to load {0!r}.'.format(filepath)) from exc

        localexts: typing.List[Extension] = []

        for key, value in module.__dict__.items():
            if inspect.isclass(value):
                if issubclass(value, Extension):
                    ext = value(self)
                    ext._unpack()

                    localexts.append(ext)
                    self._extensions[ext.__extension_name__] = ext

        if not localexts:
            raise ExtensionNotFound('No extensions were found for file {0!r}.'.format(filepath))

        return localexts

    def remove_extension(self, name: str):
        if not name in self._extensions:
            raise ExtensionNotFound('{0!r} was not found.'.format(name))

        extension = self._extensions.pop(name)
        extension._pack()

        return extension

    async def wait_for(self, event, *, timeout: int = 120.0):
        future = self.loop.create_future()
        listeners = self._listeners.get(event.lower())

        if isinstance(event, Route):
            event._waiter = future
            return await asyncio.wait_for(future, timeout=timeout)

        if not listeners:
            listeners = []
            self._listeners[event.lower()] = listeners

        listeners.append(future)
        return await asyncio.wait_for(future, timeout=timeout)
