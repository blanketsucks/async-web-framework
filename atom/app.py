from .request import Request
from .errors import *
from .http import run_server, ApplicationProtocol
from .datastructures import URL
from .router import Router
from . import utils
from .settings import Settings
from .objects import Route, Listener, Middleware, WebsocketRoute
from .views import HTTPView, WebsocketHTTPView
from .extensions import Extension
from .shards import Shard
from . import sockets
from .response import Response, JSONResponse

import inspect
import typing
import datetime
import asyncio
import pathlib
import importlib
import watchgod

__all__ = (
    'Application',
    'Extension'
)

Routes = typing.List[Route]
Listeners = typing.List[Listener]
Middlewares = typing.List[Middleware]
Extensions = typing.List[typing.Union[pathlib.Path, str]]
Shards = typing.List[Shard]

class Application:
    """
    
    ## Listeners order

    `on_startup` -> `on_connection_made` -> `on_request` -> `on_socket_receive` -> `on_connection_lost` -> `on_shutdown`
    
    """

    def __init__(self, 
                routes: Routes=...,
                listeners: Listeners=...,
                middlewares: Middlewares=...,
                extensions: Extensions=...,
                shards: Shards=...,
                *,
                loop: asyncio.AbstractEventLoop=...,
                url_prefix: str=...,
                settings_file: typing.Union[str, pathlib.Path]=...,
                load_settings_from_env: bool=...):

        routes = sockets.check_ellipsis(routes, [])
        listeners = sockets.check_ellipsis(listeners, [])

        middlewares = sockets.check_ellipsis(middlewares, [])
        extensions = sockets.check_ellipsis(extensions, [])

        shards = sockets.check_ellipsis(shards, [])

        self._ready = asyncio.Event()

        self.loop = sockets.check_ellipsis(loop, asyncio.get_event_loop())
        self.url_prefix = sockets.check_ellipsis(url_prefix, '')

        self.settings = Settings(None, False)
        self.router = Router()

        if sockets.check_ellipsis(settings_file, None):
            self.settings.from_file(settings_file)

        if sockets.check_ellipsis(load_settings_from_env, False):
            self.settings.from_env_vars()

        self.views: typing.Dict[str, typing.Union[HTTPView, WebsocketHTTPView]] = {}
        self.shards: typing.Dict[str, Shard] = {}
        self._websocket_tasks: typing.List[asyncio.Task] = []
        self._listeners: typing.Dict[str, typing.List[typing.Callable]] = {}
        self._middlewares: typing.List[typing.Callable] = []
        self._extensions: typing.Dict[str, Extension] = {}

        self._is_websocket: bool = False
        self._server = None
        self._database_connection = None

        self._backlog = 5

        self._load_from_arguments(routes, listeners, middlewares, extensions, shards)

    def __repr__(self) -> str:
        return '<Application>'

    def set_backlog(self, backlog: int):
        if self._server:
            raise ValueError('Can not set backlog once the app has started')

        self._backlog = backlog

    def _load_from_arguments(self, 
                            routes: Routes,
                            listeners: Listeners,
                            middlewares: Middlewares,
                            extensions: Extensions,
                            shards: Shards):
        
        for route in routes:
            self.add_route(route)

        for listener in listeners:
            coro = listener.coro
            name = listener.event

            self.add_listener(coro, name)

        for middleware in middlewares:
            coro = middleware.coro
            self.add_middleware(coro)

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

    async def _request_handler(self, request: Request, response_writer, *, ws):
        resp = None
        try:
            args, route = self.router.resolve(request)
            request.route = route

            if len(self._middlewares) != 0:
                await asyncio.gather(*[middleware(request, route.coro) for middleware in self._middlewares])

            args = self._convert(route.coro, args)

            if isinstance(route, WebsocketRoute):
                self.loop.create_task(
                    coro=route(request, ws)
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
            await self.dispatch('on_error', exc)

        await response_writer(resp)

    async def wait_until_startup(self):
        await self._ready.wait()

    def is_ready(self):
        return self._ready.is_set()

    @property
    def listeners(self):
        return self._listeners

    @property
    def middlewares(self):
        return self._middlewares

    @property
    def extensions(self):
        return self._extensions

    async def start(self,
                    host: str = ...,
                    port: int = ...,
                    *,
                    debug: bool = ...):
        debug = False if debug is ... else debug

        protocol = ApplicationProtocol(
            app=self,
            loop=self.loop
        )

        if debug:
            await self._watch_for_changes()

        await run_server(
            protocol=protocol,
            app=self,
            host=host,
            port=port,
            loop=self.loop
        )

    async def close(self):
        server = self._server

        if not server:
            raise ApplicationError('The Application is not running')

        server.close()
        await self.dispatch('on_shutdown')

    def run(self, *args: typing.Tuple, **kwargs: typing.Mapping):
        try:
            return self.loop.run_until_complete(self.start(*args, **kwargs))
        except KeyboardInterrupt:
            return self.loop.run_until_complete(self.close())
        finally:
            return self.loop.close()

    def websocket(self, path: str):
        def decorator(coro) -> WebsocketRoute:
            route = WebsocketRoute(path, 'GET', coro)
            route.subprotocols = tuple()

            return self.add_route(route)

        return decorator

    def route(self, path: typing.Union[str, URL], method: str):
        def decorator(func: typing.Callable):
            actual = path

            if isinstance(path, URL):
                actual = path.path

            route = Route(actual, method, func)
            return self.add_route(route)

        return decorator

    def add_route(self, route: typing.Union[Route, WebsocketRoute]):
        if not isinstance(route, (Route, WebsocketRoute)):
            fmt = 'Expected Route or WebsocketRoute but got {0!r} instead'
            raise RouteRegistrationError(fmt.format(route.__class__.__name__))

        if not inspect.iscoroutinefunction(route.coro):
            raise RouteRegistrationError('Routes must be async.')

        if route in self.router.routes:
            raise RouteRegistrationError('{0!r} is already a route.'.format(route.path))

        if isinstance(route, WebsocketRoute):
            self.router.add_route(route.path, route.method, route.coro, websocket=True)
            return route

        self.router.add_route(route.path, route.method, route.coro)
        return route

    def get(self, path: typing.Union[str, URL]):
        def decorator(func) -> Route:
            return self.route(path, 'GET')(func)
        return decorator

    def put(self, path: typing.Union[str, URL]):
        def decorator(func):
            return self.route(path, 'PUT')(func)
        return decorator

    def post(self, path: typing.Union[str, URL]):
        def decorator(func):
            return self.route(path, 'POST')(func)
        return decorator

    def delete(self, path: typing.Union[str, URL]):
        def decorator(func):
            return self.route(path, 'DELETE')(func)
        return decorator

    def head(self, path: typing.Union[str, URL]):
        def decorator(func):
            return self.route(path, 'HEAD')(func)
        return decorator

    def options(self, path: typing.Union[str, URL]):
        def decorator(func):
            return self.route(path, 'OPTIONS')(func)
        return decorator

    def patch(self, path: typing.Union[str, URL]):
        def decorator(func):
            return self.route(path, 'PATCH')(func)
        return decorator


    def remove_route(self, route: typing.Union[Route, WebsocketRoute]):
        self.router.routes.remove(route)
        return route

    # dispatching and listeners

    def add_listener(self, coro: typing.Callable, name: str = None):
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

    def remove_listener(self, func: typing.Callable = None, name: str = None):
        if not func:
            if name:
                coros = self._listeners.pop(name.lower())
                return coros

            raise TypeError('Only the function or the name can be None, not both.')

        self._listeners[name].remove(func)

    def listen(self, name: str = None):
        def decorator(func: typing.Callable):
            return self.add_listener(func, name)

        return decorator

    async def dispatch(self, name: str, *args, **kwargs):
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

        return await asyncio.gather(*[listener(*args, **kwargs) for listener in listeners], loop=self.loop)

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

        for route in view.as_routes():
            self.add_route(route)

        self.views[view.__path__] = view
        return view

    def register_websocket_view(self, view: WebsocketHTTPView):
        if not isinstance(view, WebsocketHTTPView):
            raise ViewRegistrationError(
                'Expected WebsocketHTTPView but got {0!r} instead.'.format(view.__class__.__name__))

        for route in view.as_routes():
            self.add_route(route, websocket=True)

        self.views[view.__url_route__] = view
        return view

    def view(self, path: str):
        def decorator(cls):
            if cls.__url_route__ == '':
                cls.__url_route__ = path

            return self.register_view(cls)

        return decorator

    def middleware(self):
        def wrapper(func: typing.Callable):
            return self.add_middleware(func)

        return wrapper

    def add_middleware(self, middleware: typing.Callable):
        if not inspect.iscoroutinefunction(middleware):
            raise MiddlewareRegistrationError('All middlewares must be async')

        self._middlewares.append(middleware)
        return Middleware(middleware)

    def remove_middleware(self, middleware: typing.Callable) -> typing.Callable:
        self._middlewares.remove(middleware)
        return middleware

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

    async def wait_for(self, event: str, *, timeout: int = 120.0):
        future = self.loop.create_future()
        listeners = self._listeners.get(event.lower())

        if not listeners:
            listeners = []
            self._listeners[event.lower()] = listeners

        listeners.append(future)
        return await asyncio.wait_for(future, timeout=timeout)
