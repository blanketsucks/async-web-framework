from typing import Any, Callable, Coroutine, Dict, List, Optional, Tuple, Union
import pathlib
import re
import inspect
import datetime
import asyncio

from .abc import AbstractRouter, AbstractProtocol, AbstractApplication
from .request import Request
from .errors import *
from .protocol import ApplicationProtocol
from .router import Router
from . import utils
from .settings import Settings
from .objects import Route, Listener, WebsocketRoute
from .views import HTTPView
from .response import Response, JSONResponse, FileResponse
from .file import File
from .websockets import Websocket

__all__ = (
    'Application',
)

class Application(AbstractApplication):
    def __init__(self, 
                url_prefix: str=None, 
                *, 
                loop: asyncio.AbstractEventLoop=None,
                settings_file: Union[str, pathlib.Path]=None, 
                load_settings_from_env: bool=None,
                supress_warnings: bool=False):
        self.loop = self._get_event_loop(loop)
        self.url_prefix = url_prefix or ''
        self.router: AbstractRouter = Router()
        self.websocket_tasks: List[asyncio.Task] = []
        self.settings = Settings()
        self.surpress_warnings = supress_warnings

        if settings_file is not None:
            self.settings = Settings.from_file(settings_file)

        if load_settings_from_env is True:
            self.settings = Settings.from_env_vars()

        self._listeners: Dict[str, List[Callable]] = {}
        self._views: Dict[str, HTTPView] = {}
        self._middlewares: List[Callable] = []
        self._active_listeners: List[asyncio.Task] = []
        self._protocol = ApplicationProtocol(
            app=self,
        )
        self._server = None
        self._closed = False

    def __repr__(self) -> str:
        prefix = self.url_prefix or '/'
        return f'<Application url_prefix={prefix!r} is_closed={self.is_closed()}>'

    @staticmethod
    async def _maybe_coroutine(func, *args, **kwargs):
        if asyncio.iscoroutinefunction(func):
            return await func(*args, **kwargs)

        return func(*args, **kwargs)

    @staticmethod
    def _get_event_loop(loop=None):
        if loop:
            if not isinstance(loop, asyncio.AbstractEventLoop):
                raise TypeError('Invalid argument type for loop argument')

            return loop

        try:
            return asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.get_event_loop()

    def _ensure_listeners(self):
        for task in self._active_listeners:
            if task.done():
                self._active_listeners.remove(task)

    def _ensure_websockets(self):
        for ws in self.websocket_tasks:
            if ws.done():
                self.websocket_tasks.remove(ws)

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

    def _resolve(self, request: 'Request') -> Tuple[Dict, Union[Route, WebsocketRoute]]:
        for route in self.router:
            match = re.fullmatch(route.path, request.url.path)

            if match is None:
                continue

            if match:
                if route.method != request.method:
                    raise BadRequest(reason=f"{request.method!r} is not allowed for {request.url.path!r}")

                return match.groupdict(), route

        raise NotFound(reason=f'Could not find {request.url.path!r}')

    def _parse_response(self, response: Union[str, bytes, dict, list, File, Response]) -> bytes:
        if isinstance(response, Response):
            return response.encode()

        if isinstance(response, str):
            resp = Response(response, content_type='text/html')
            return resp.encode()

        if isinstance(response, (dict, list)):
            resp = JSONResponse(response)
            return resp.encode()

        if isinstance(response, File):
            resp = FileResponse(response)
            return resp.encode()

        if isinstance(response, bytes):
            return response

        return b''

    async def _run_middlewares(self, request: Request, route: Route, args: Tuple[Any]):
        middlewares = route.middlewares.copy()
        middlewares.extend(self._middlewares)

        await asyncio.gather(
            *[middleware(route, request, *args) for middleware in middlewares],
        )

    def _handle_websocket_connection(self, route: WebsocketRoute, request: Request, websocket: Websocket):
        coro = route(request, websocket)
        task = self.loop.create_task(coro)

        self.websocket_tasks.append(task)
        self._ensure_websockets()

        return task

    def _resolve_all(self, request: Request):
        args, route = self._resolve(request)
        request.route = route

        args = self._convert(route.callback, args)
        return args, route

    async def _request_handler(self, request: Request, *, websocket: Websocket):
        resp = None
        try:
            args, route = self._resolve_all(request)
    
            await self._run_middlewares(
                request=request,
                route=route,
                args=args,
            )
            if isinstance(route, WebsocketRoute):
                return self._handle_websocket_connection(
                    route=route,
                    request=request,
                    websocket=websocket,
                )

            resp = await self._maybe_coroutine(route.callback, request, *args)
        except Exception as exc:
            resp = utils.format_exception(exc)
            self.dispatch('error', exc)

        data = self._parse_response(resp)

        transport = self.get_transport()
        transport.write(data)

        transport.close()

    @property
    def listeners(self):
        return self._listeners

    @property
    def websockets(self):
        return self._protocol.websockets

    @property
    def protocol(self):
        return self._protocol

    @protocol.setter
    def protocol(self, value):
        if not isinstance(value, asyncio.Protocol):
            raise ValueError('Expected asyncio.Protocol but got {0.__class__.__name__} instead'.format(value))

        self._protocol = value
    
    def is_closed(self):
        return self._closed

    def get_transport(self) -> Optional[asyncio.Transport]:
        return getattr(self._protocol, 'transport', None)

    def get_request_task(self) -> Optional[asyncio.Task]:
        return getattr(self._protocol, 'request', None)

    def log(self, message: str):
        print(f'[{datetime.datetime.utcnow().strftime("%Y/%m/%d | %H:%M:%S")}] {message}')

    async def start(self, host: str=None, port: int=None):
        host = host or '127.0.0.1'
        port = port or 8080

        server: asyncio.AbstractServer = await self.loop.create_server(self._protocol, host, port)
        self._server = server

        self.dispatch('startup')
        await server.serve_forever()

    async def wait_closed(self):
        self._ensure_listeners()
        self.protocol.ensure_websockets()

        for websocket in self.websockets.values():
            ws = self.websockets.pop(websocket.peer)
            ws.close(b'')
            
        for task in self.websocket_tasks:
            if not task.done():
                task.cancel()

        for listener in self._active_listeners:
            if not listener.done():
                listener.cancel()

        transport = self.get_transport()
        if transport:
            transport.close()

        request = self.get_request_task()
        if request:
            if not request.done():
                request.cancel()

        self._active_listeners.clear()
        self.websocket_tasks.clear()
        self._protocol.websockets.clear()

        await self._server.wait_closed()

    def close(self):
        if not self._server:
            raise ApplicationError('The Application is not running')

        self._server.close()
        self._closed = True

        self.dispatch('shutdown')

    def run(self, *args, **kwargs):
        # async def runner():
        #     try:
        #         await self.start(*args, **kwargs)
        #     except:
        #         await self.wait_closed()
        #         self.close()

        # self.loop.create_task(coro=runner())
        # self.loop.run_forever()
        
        self.loop.run_until_complete(self.start(*args, **kwargs))

    def websocket(self, path: str):
        def decorator(coro: Callable[..., Coroutine]) -> WebsocketRoute:
            route = WebsocketRoute(path, 'GET', coro, app=self)
            route.subprotocols = tuple()

            return self.add_route(route)
        return decorator

    def route(self, path: str, method: str):
        def decorator(func: Callable[..., Coroutine]) -> Route:
            actual = path

            route = Route(actual, method, func, router=self.router)
            return self.add_route(route)

        return decorator

    def add_route(self, route: Union[Route, WebsocketRoute]):
        if not isinstance(route, (Route, WebsocketRoute)):
            fmt = 'Expected Route or WebsocketRoute but got {0!r} instead'
            raise RegistrationError(fmt.format(route.__class__.__name__))

        if not inspect.iscoroutinefunction(route.callback):
            if not self.surpress_warnings:
                fmt = (
                    'This framework does support synchronous routes but due to everything being done in asynchronous manner it\'s not recommended'
                )
                utils.warn(
                    message=fmt,
                    category=Warning,
                )

        if route in self.router:
            raise RegistrationError('{0!r} is already a route.'.format(route.path))

        return self.router.add_route(route)

    def add_router(self, router: Router):
        if not isinstance(router, Router):
            fmt = 'Expected Router but got {0!r} instead'
            raise TypeError(fmt.format(router.__class__.__name__))

        for route in router:
            self.add_route(route)
        
        return router

    def get_route(self, method: str, path: str):
        res = (path, method)
        route = self.router.routes.get(res)

        return route

    def get(self, path: str):
        def decorator(func: Callable[..., Coroutine]) -> Route:
            return self.route(path, 'GET')(func)
        return decorator

    def put(self, path: str):
        def decorator(func: Callable[..., Coroutine]):
            return self.route(path, 'PUT')(func)
        return decorator

    def post(self, path: str):
        def decorator(func: Callable[..., Coroutine]):
            return self.route(path, 'POST')(func)
        return decorator

    def delete(self, path: str):
        def decorator(func: Callable[..., Coroutine]):
            return self.route(path, 'DELETE')(func)
        return decorator

    def head(self, path: str):
        def decorator(func: Callable[..., Coroutine]):
            return self.route(path, 'HEAD')(func)
        return decorator

    def options(self, path: str):
        def decorator(func: Callable[..., Coroutine]):
            return self.route(path, 'OPTIONS')(func)
        return decorator

    def patch(self, path: str):
        def decorator(func: Callable[..., Coroutine]):
            return self.route(path, 'PATCH')(func)
        return decorator

    def remove_route(self, route: Union[Route, WebsocketRoute]):
        self.router.routes.pop((route.path, route.method))
        return route

    def add_event_listener(self, coro: Callable[..., Coroutine], name: str = None):
        if not inspect.iscoroutinefunction(coro):
            raise RegistrationError('Listeners must be coroutines')

        actual = name if name else coro.__name__

        if actual in self._listeners.keys():
            self._listeners[actual].append(coro)
            return Listener(coro, actual)

        self._listeners[actual] = [coro]
        return Listener(coro, actual)

    def remove_event_listener(self, func: Callable[..., Coroutine] = None, name: str = None):
        if not func:
            if name:
                self._listeners.pop(name.lower())

            raise TypeError('Only the function or the name can be None, not both.')

        self._listeners[name].remove(func)

    def event(self, name: str = None):
        def decorator(func: Callable[..., Coroutine]):
            return self.add_event_listener(func, name)
        return decorator

    def dispatch(self, name: str, *args, **kwargs):
        self._ensure_listeners()
        name = 'on_' + name

        try:
            listeners = self._listeners[name]
        except KeyError:
            coro = getattr(self, name, None)
            if not coro:
                return

            listeners = [coro]

        for listener in listeners:
            task = self.loop.create_task(listener(*args, **kwargs))
            self._active_listeners.append(task)

    def get_view(self, path: str):
        return self._views.get(path)

    def register_view(self, view: HTTPView):
        if not isinstance(view, HTTPView):
            raise RegistrationError('Expected HTTPView but got {0!r} instead.'.format(view.__class__.__name__))

        for route in view.as_routes(app=self):
            self.add_route(route)

        self._views[view.__url_route__] = view
        return view

    def view(self, path: str):
        def decorator(cls):
            if cls.__url_route__ == '':
                cls.__url_route__ = path

            view = cls()
            return self.register_view(view)
        return decorator

    def middleware(self, func):
        if not inspect.iscoroutinefunction(func):
            raise RegistrationError('Middlewares must be coroutines')

        self._middlewares.append(func)
        return func
