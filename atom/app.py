from typing import Any, Callable, Coroutine, Dict, List, Optional, Tuple, Union
import pathlib
import re
import inspect
import datetime
import logging
import asyncio

from .abc import AbstractRouter, AbstractProtocol, AbstractApplication, AbstractConnection
from .request import Request
from .responses import NotFound, MethodNotAllowed
from .errors import *
from .protocol import ApplicationProtocol, Connection
from .router import Router
from . import utils
from .settings import Settings
from .objects import PartialRoute, Route, Listener, WebsocketRoute
from .views import HTTPView
from .response import Response, JSONResponse, FileResponse, HTMLResponse
from .file import File
from .websockets import Websocket

log = logging.getLogger(__name__)

__all__ = (
    'Application',
    'run'
)

class Application(AbstractApplication):
    """
    A class respreseting an ASGI application.

    Attributes:
        router: A [Router](./router.md) instance.
        settings: A [Settings](./settings.md) instance.
        suppress_warnings: A bool indicating whether warnings should be surpressed.
    """
    def __init__(self,
                url_prefix: str=None, 
                *, 
                settings_file: Union[str, pathlib.Path]=None, 
                load_settings_from_env: bool=None,
                suppress_warnings: bool=False):
        """
        Constructor.

        Args:
            url_prefix: A string to prefix all routes with.
            settings_file: A string or pathlib.Path instance to a settings file to load.
            load_settings_from_env: A bool indicating whether to load settings from the environment.
            suppress_warnings: A bool indicating whether to surpress warnings.
        """
        self.url_prefix = url_prefix or ''
        self.router: AbstractRouter = Router()
        self.websocket_tasks: List[asyncio.Task] = []
        self.settings = Settings()
        self.suppress_warnings = suppress_warnings

        if settings_file is not None:
            self.settings = Settings.from_file(settings_file)

        if load_settings_from_env is True:
            self.settings = Settings.from_env_vars()

        self._listeners: Dict[str, List[Callable]] = {}
        self._views: Dict[str, HTTPView] = {}
        self._middlewares: List[Callable] = []
        self._active_listeners: List[asyncio.Task] = []
        self._loop = None
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
                    raise MethodNotAllowed(reason=f"{request.method!r} is not allowed for {request.url.path!r}")

                return match.groupdict(), route

        raise NotFound(reason=f'Could not find {request.url.path!r}')

    async def _parse_response(self, response: Union[str, bytes, dict, list, File, Response]) -> bytes:
        if isinstance(response, Response):
            if isinstance(response, FileResponse):
                await response.read(self.loop)
                response.file.close()

                return response.encode()

            return response.encode()

        if isinstance(response, str):
            resp = HTMLResponse(response)
            return resp.encode()

        if isinstance(response, (dict, list)):
            resp = JSONResponse(response)
            return resp.encode()

        if isinstance(response, File):
            resp = FileResponse(response)
            await resp.read(self.loop)

            response.close()
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

    async def _request_handler(self, request: Request, connection: Connection, *, websocket: Websocket):
        resp = None
        route = None

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
            if not route:
                route = PartialRoute(
                    path=request.url.path,
                    method=request.method
                )

            resp = utils.format_exception(exc)
            self.dispatch('error', route, request, exc)

        data = await self._parse_response(resp)
        await connection.write(data)

        connection.close()

    @property
    def listeners(self) -> Dict[str, List[Callable[..., Coroutine]]]:
        """
        Returns:
            A dictionary of all listeners.
        """
        return self._listeners

    @property
    def websockets(self) -> Dict[Tuple[str, int], Websocket]:
        """
        Returns:
            A dict contaning the current websocket connections.
        """
        return self._protocol.websockets

    @property
    def connections(self) -> Dict[Tuple[str, int], AbstractConnection]:
        """
        Returns:
            A list of all connections.
        """
        return self._protocol.connections

    @property
    def protocol(self) -> AbstractProtocol:
        """
        Returns:
            The current protocol.
        """
        return self._protocol

    @protocol.setter
    def protocol(self, value):
        if not isinstance(value, AbstractProtocol):
            raise ValueError('Expected AbstractProtocol but got {0.__class__.__name__} instead'.format(value))

        self._protocol = value

    @property
    def loop(self) -> Optional[asyncio.AbstractEventLoop]:
        return self._loop
    
    def is_closed(self) -> bool:
        """
        Whether or not the application has been closed

        Returns:
            True if the application has been closed, False otherwise.

        """
        return self._closed

    def log(self, message: str):
        print(f'[{datetime.datetime.utcnow().strftime("%Y/%m/%d | %H:%M:%S")}] {message}')

    async def start(self, host: Optional[str]=None, port: Optional[int]=None):
        """
        Starts the application.

        Args:
            host: The host to listen on.
            port: The port to listen on.
        """
        self._loop = self._get_event_loop()
        self._protocol.loop = self.loop

        host = host or '127.0.0.1'
        port = port or 8080

        server: asyncio.AbstractServer = await self.loop.create_server(self._protocol, host, port)
        self._server = server

        self.dispatch('startup')
        log.info(f'Started listening on {host}:{port}')

        await server.serve_forever()

    async def wait_closed(self):
        """
        Waits till the application has finished cleaning up.
        """
        log.info(f'Waiting for application to close...')

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

        conn = self.get_current_connection()
        if conn:
            conn.close()

        self._active_listeners.clear()
        self.websocket_tasks.clear()
        self._protocol.websockets.clear()

        await self._server.wait_closed()

    def close(self):
        """
        Closes the application.
        """
        if not self._server:
            raise ApplicationError('The Application is not running')

        self._server.close()
        self._closed = True

        self.dispatch('shutdown')
        log.info(f'Closed application')

    def websocket(self, path: str):
        def decorator(coro: Callable[..., Coroutine]) -> WebsocketRoute:
            route = WebsocketRoute(path, 'GET', coro, router=self.router)
            return self.add_route(route)
        return decorator

    def route(self, path: str, method: str=None):
        method = method or 'GET'

        def decorator(func: Callable[..., Coroutine]) -> Route:
            route = Route(path, method, func, router=self.router)
            return self.add_route(route)
        return decorator

    def add_route(self, route: Union[Route, WebsocketRoute]):
        if not isinstance(route, (Route, WebsocketRoute)):
            fmt = 'Expected Route or WebsocketRoute but got {0!r} instead'
            raise RegistrationError(fmt.format(route.__class__.__name__))

        if not inspect.iscoroutinefunction(route.callback):
            if not self.suppress_warnings:
                fmt = (
                    'This framework does support synchronous routes but due to everything being done in asynchronous manner it\'s not recommended'
                )
                utils.warn(
                    message=fmt,
                    category=Warning,
                )

                log.warn(fmt)

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
        log.debug(f'Dispatching event: {name}')

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

        routes = view.as_routes(router=self.router)
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

    # async def on_error(self, 
    #                 route: Union[Route, PartialRoute], 
    #                 request: Request, 
    #                 exception: Exception):
    #     raise exception

async def run(app: Application, *args, **kwargs):
    try:
        await app.start(*args, **kwargs)
    finally:
        await app.wait_closed()
        app.close()

    return app