import ssl
from typing import Any, Callable, Coroutine, Dict, List, Optional, Tuple, Union
import pathlib
import re
import inspect
import logging
import multiprocessing
import socket
import asyncio

from . import compat
from . import utils
from . import abc
from .server import ClientConnection
from .request import Request
from .responses import NotFound, MethodNotAllowed
from .errors import *
from .router import Router
from .settings import Settings
from .objects import PartialRoute, Route, Listener, WebsocketRoute
from .views import HTTPView
from .response import Response, JSONResponse, FileResponse, HTMLResponse
from .file import File
from .websockets import Websocket
from .workers import Worker
from .models import Model

log = logging.getLogger(__name__)

__all__ = (
    'Application',
    'run'
)

class Application(abc.AbstractApplication):
    """
    A class respreseting an ASGI application.

    Attributes:
        router: A [Router](./router.md) instance.
        settings: A [Settings](./settings.md) instance.
        suppress_warnings: A bool indicating whether warnings should be surpressed.
    """
    def __init__(self,
                host: str=None,
                port: int=None,
                url_prefix: str=None, 
                *,
                worker_count: int=None, 
                settings_file: Union[str, pathlib.Path]=None, 
                load_settings_from_env: bool=None,
                suppress_warnings: bool=False,
                use_ssl: bool=False,
                ssl_context: ssl.SSLContext=None):
        """
        Constructor.

        Args:
            url_prefix: A string to prefix all routes with.
            settings_file: A string or pathlib.Path instance to a settings file to load.
            load_settings_from_env: A bool indicating whether to load settings from the environment.
            suppress_warnings: A bool indicating whether to surpress warnings.
        """
        self.host = host or '127.0.0.1'
        self.port = port or 8080

        self.url_prefix = url_prefix or ''
        self.router: abc.AbstractRouter = Router()
        self.websocket_tasks: List[asyncio.Task] = []
        self.settings = Settings()
        self.worker_count = worker_count or (multiprocessing.cpu_count() * 2) + 1
        self.suppress_warnings = suppress_warnings
        self.is_ssl = use_ssl
        self.ssl_context = ssl_context

        if self.is_ssl and self.ssl_context is None:
            self.ssl_context = ssl.create_default_context()

        if settings_file is not None:
            self.settings = Settings.from_file(settings_file)

        if load_settings_from_env is True:
            self.settings = Settings.from_env_vars()

        self._listeners: Dict[str, List[Callable]] = {}
        self._views: Dict[str, HTTPView] = {}
        self._middlewares: List[Callable] = []
        self._active_listeners: List[asyncio.Task] = []

        self._loop = None
        self._closed = False

        self._socket = self._make_socket()
        self._workers = self._add_workers()

    def __repr__(self) -> str:
        prefix = self.url_prefix or '/'
        return f'<Application url_prefix={prefix!r} is_closed={self.is_closed()}>'

    async def __aenter__(self):
        await self.start()
        return self
    
    async def __aexit__(self, *args):
        await self.close()
        return self

    @staticmethod
    async def _maybe_coroutine(func, *args, **kwargs):
        if asyncio.iscoroutinefunction(func):
            return await func(*args, **kwargs)

        return func(*args, **kwargs)

    def _add_workers(self):
        workers = {}

        for i in range(self.worker_count):
            worker = Worker(self, i)
            workers[worker.id] = worker
        
        return workers

    def _make_socket(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        addr = (self.host, self.port)
        sock.bind(addr)
        
        return sock

    def _ensure_listeners(self):
        for task in self._active_listeners:
            if task.done():
                self._active_listeners.remove(task)

    def _ensure_websockets(self):
        for ws in self.websocket_tasks:
            if ws.done():
                self.websocket_tasks.remove(ws)

    def _convert(self, func: Callable, args: Dict, request: 'Request'):
        return_args = []
        params = inspect.signature(func)

        for key, value in params.parameters.items():
            param = args.get(key)
            if param:
                if value.annotation is inspect.Signature.empty:
                    return_args.append(param)
                else:
                    try:
                        param = value.annotation(param)
                    except ValueError:
                        fut = 'Failed conversion to {0!r} for parameter {1!r}.'.format(value.annotation.__name__, key)
                        raise BadConversion(fut) from None
                    else:
                        return_args.append(param)

            else:
                if issubclass(value.annotation, Model):
                    data = request.json()
                    model = value.annotation.from_json(data.get(key))

                    return_args.append(model)

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
        status = 200
        if isinstance(response, tuple):
            response, status = response

            if not isinstance(status, int):
                raise TypeError('Response status must be an integer.')

        if isinstance(response, File):
            response = FileResponse(response, status=status)  

        if isinstance(response, Response):
            if isinstance(response, FileResponse):
                await response.read()
                response.file.close()

                return response.encode()

            return response.encode()

        if isinstance(response, Model):
            resp = JSONResponse(response.json(), status=status)
            return resp

        if isinstance(response, str):
            resp = HTMLResponse(response, status=status)
            return resp.encode()

        if isinstance(response, (dict, list)):
            resp = JSONResponse(response, status=status)
            return resp.encode()

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

        args = self._convert(route.callback, args, request)
        return args, route

    async def _request_handler(self, 
                        request: Request, 
                        connection: ClientConnection, 
                        websocket: Websocket,
                        worker: abc.AbstractWorker):
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

            self.dispatch('error', route, request, worker, exc)
            return

        data = await self._parse_response(resp)
        await connection.write(data)

        connection.close()

    @property
    def workers(self) -> List[Worker]:
        return list(self._workers.values())

    @property
    def socket(self) -> socket.socket:
        return self._socket

    @property
    def listeners(self) -> Dict[str, List[Callable[..., Coroutine]]]:
        """
        Returns:
            A dictionary of all listeners.
        """
        return self._listeners

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

    def is_serving(self):
        return all([worker.is_serving() for worker in self.workers])

    def get_worker(self, id: int) -> Optional[Worker]:
        return self._workers.get(id)

    def add_worker(self, worker: abc.AbstractWorker):
        if not isinstance(worker, abc.AbstractWorker):
            raise TypeError('worker must be an instance of AbstractWorker')

        if worker.id in self._workers:
            raise ValueError(f'Worker with id {worker.id} already exists')

        self._workers[worker.id] = worker
        return worker

    async def start(self):
        """
        Starts the application.

        Args:
            host: The host to listen on.
            port: The port to listen on.
        """
        self._loop = loop = compat.get_running_loop()

        for worker in self.workers:
            self.loop.create_task(worker.run(loop), name=f'Worker-{worker.id}')

        self.dispatch('startup')

    async def close(self):
        """
        Closes the application.
        """
        for worker in self.workers:
            await worker.stop()

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
            route = Route(path, 'GET', func, router=self.router)
            return self.add_route(route)
        return decorator

    def put(self, path: str):
        def decorator(func: Callable[..., Coroutine]):
            route = Route(path, 'PUT', func, router=self.router)
            return self.add_route(route)
        return decorator

    def post(self, path: str):
        def decorator(func: Callable[..., Coroutine]):
            route = Route(path, 'POST', func, router=self.router)
            return self.add_route(route)
        return decorator

    def delete(self, path: str):
        def decorator(func: Callable[..., Coroutine]):
            route = Route(path, 'DELETE', func, router=self.router)
            return self.add_route(route)
        return decorator

    def head(self, path: str):
        def decorator(func: Callable[..., Coroutine]):
            route = Route(path, 'HEAD', func, router=self.router)
            return self.add_route(route)
        return decorator

    def options(self, path: str):
        def decorator(func: Callable[..., Coroutine]):
            route = Route(path, 'OPTIONS', func, router=self.router)
            return self.add_route(route)
        return decorator

    def patch(self, path: str):
        def decorator(func: Callable[..., Coroutine]):
            route = Route(path, 'PATCH', func, router=self.router)
            return self.add_route(route)
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
                return

            raise TypeError('Only the function or the name can be None, not both.')

        self._listeners[name].remove(func)

    def event(self, name: str = None):
        def decorator(func: Callable[..., Coroutine]):
            return self.add_event_listener(func, name)
        return decorator

    def dispatch(self, name: str, *args, **kwargs):
        loop = self.loop
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

        tasks = [loop.create_task(listener(*args, **kwargs)) for listener in listeners]
        self._active_listeners.extend(tasks)

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

    async def on_error(self, 
                    route: Union[Route, PartialRoute], 
                    request: Request,
                    worker: abc.AbstractWorker, 
                    exception: Exception):
        raise exception

async def run(app: Application):
    try:
        await app.start()
        loop = app._loop
        
        fut = loop.create_future()
        await fut
    finally:
        await app.close()

    return app