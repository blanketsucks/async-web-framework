import ssl
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Union
import pathlib
import re
import inspect
import logging
import multiprocessing
import socket
import asyncio
import traceback

from ._types import CoroFunc, MaybeCoroFunc

from . import compat, utils
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


class Application:
    """
    A class respreseting an ASGI application.

    Attributes:
        router: A [Router](./router.md) instance.
        settings: A [Settings](./settings.md) instance.
        suppress_warnings: A bool indicating whether warnings should be surpressed.
    """
    def __init__(self,
                host: Optional[str]=None,
                port: Optional[int]=None,
                url_prefix: Optional[str]=None, 
                *,
                worker_count: Optional[int]=None, 
                settings_file: Optional[Union[str, pathlib.Path]]=None, 
                load_settings_from_env: Optional[bool]=None,
                suppress_warnings: Optional[bool]=False,
                use_ssl: Optional[bool]=False,
                ssl_context: Optional[ssl.SSLContext]=None):
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
        self.router = Router()
        self.websocket_tasks: List[asyncio.Task[Any]] = []
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

        self._listeners: Dict[str, List[CoroFunc]] = {}
        self._views: Dict[str, HTTPView] = {}
        self._middlewares: List[CoroFunc] = []
        self._active_listeners: List[asyncio.Task[Any]] = []

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
    
    async def __aexit__(self, *args: Any):
        await self.close()
        return self

    @staticmethod
    async def _maybe_coroutine(func: MaybeCoroFunc[Any], *args: Any, **kwargs: Any) -> Any:
        if asyncio.iscoroutinefunction(func):
            return await func(*args, **kwargs)

        return func(*args, **kwargs)

    def _add_workers(self):
        workers: Dict[int, Worker] = {}

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

    def _convert(self, func: CoroFunc, args: Dict[str, Any], request: 'Request') -> Dict[str, Any]:
        kwargs: Dict[str, Any] = {}
        params = inspect.signature(func)

        for key, value in params.parameters.items():
            param = args.get(key)
            if param:
                if value.annotation is inspect.Signature.empty:
                    kwargs[key] = param
                else:
                    try:
                        param = value.annotation(param)
                    except ValueError:
                        fut = 'Failed conversion to {0!r} for parameter {1!r}.'.format(value.annotation.__name__, key)
                        raise BadConversion(fut) from None
                    else:
                        kwargs[key] = param

            else:
                if issubclass(value.annotation, Model):
                    data = request.json()
                    data = data.get(key)

                    if data:
                        model = value.annotation.from_json(data)

                    else:
                        raise ValueError

                    kwargs[key] = model

        return kwargs

    def _resolve(self, request: 'Request') -> Tuple[Dict[str, Any], Union[Route, WebsocketRoute]]:
        for route in self.router:
            match = re.fullmatch(route.path, request.url.path)

            if match is None:
                continue

            if match:
                if route.method != request.method:
                    raise MethodNotAllowed(reason=f"{request.method!r} is not allowed for {request.url.path!r}")

                return match.groupdict(), route

        raise NotFound(reason=f'Could not find {request.url.path!r}')

    def _validate_status_code(self, code: int):
        if 300 <= code <= 399:
            ret = 'Redirect status codes cannot be returned, use Request.redirect instead'
            raise ValueError(ret)

        if not (200 <= code <= 599):
            ret = f'Status code {code} is not valid'
            raise ValueError(ret)

        return code

    async def parse_response(self, response: Union[str, bytes, Dict[str, Any], List[Any], Tuple[Any, Any], File, Response, Any]) -> Optional[Response]:
        status = 200

        if isinstance(response, tuple):
            response, status = response

            if not isinstance(status, int):
                raise TypeError('Response status must be an integer.')

            status = self._validate_status_code(status)

        if isinstance(response, File):
            response = FileResponse(response, status=status)  

        if isinstance(response, Response):
            if isinstance(response, FileResponse):
                await response.read()
                response.file.close()

            return response

        if isinstance(response, Model):
            resp = JSONResponse(response.json(), status=status)
            return resp

        if isinstance(response, bytes):
            response = response.decode()

        if isinstance(response, str):
            resp = HTMLResponse(response, status=status)
            return resp

        if isinstance(response, (dict, list)):
            resp = JSONResponse(response, status=status)
            return resp

    async def _run_middlewares(self, request: Request, route: Route,  kwargs: Dict[str, Any]):
        middlewares = route.middlewares.copy()
        middlewares.extend(self._middlewares)

        await asyncio.gather(
            *[middleware(route, request, **kwargs) for middleware in middlewares],
        )

    def _handle_websocket_connection(self, route: WebsocketRoute, request: Request, websocket: Websocket):
        if not self.loop:
            return

        coro = route(request, websocket)
        task = self.loop.create_task(coro, name=f'Websocket-{request.url.path}')

        self.websocket_tasks.append(task)
        self._ensure_websockets()

        return task

    def _resolve_all(self, request: Request):
        args, route = self._resolve(request)
        request.route = route

        kwargs = self._convert(route.callback, args, request)
        return kwargs, route

    async def _request_handler(self, 
                        request: Request, 
                        connection: ClientConnection, 
                        websocket: Websocket,
                        worker: Worker):
        resp = None
        route = None

        try:
            kwargs, route = self._resolve_all(request)

            await self._run_middlewares(
                request=request,
                route=route,
                kwargs=kwargs,
            )

            if request.is_closed():
                return

            if isinstance(route, WebsocketRoute):
                return self._handle_websocket_connection(
                    route=route,
                    request=request,
                    websocket=websocket,
                )

            resp = await self._maybe_coroutine(route.callback, request, **kwargs)
        except Exception as exc:
            if not route:
                route = PartialRoute(
                    path=request.url.path,
                    method=request.method
                )

            self.dispatch('error', route, request, worker, exc)
            return

        await request.send(resp)
        await request.close()

    @property
    def workers(self) -> List[Worker]:
        return list(self._workers.values())

    @property
    def views(self) -> List[HTTPView]:
        return list(self._views.values())

    @property
    def socket(self) -> socket.socket:
        return self._socket

    @property
    def listeners(self) -> Dict[str, List[CoroFunc]]:
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

    def add_worker(self, worker: Union[Worker, Any]) -> Worker:
        if not isinstance(worker, Worker):
            raise TypeError('worker must be an instance of Worker')

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
            loop.create_task(worker.run(loop), name=f'Worker-{worker.id}')

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

    def websocket(self, path: str) -> Callable[[CoroFunc], WebsocketRoute]:
        def decorator(coro: CoroFunc) -> WebsocketRoute:
            route = WebsocketRoute(path, 'GET', coro, router=self.router)
            self.add_route(route)

            return route
        return decorator

    def route(self, path: str, method: Optional[str]=None) -> Callable[[CoroFunc], Route]:
        actual = method or 'GET'

        def decorator(func: CoroFunc) -> Route:
            route = Route(path, actual, func, router=self.router)
            return self.add_route(route)
        return decorator

    def add_route(self, route: Union[Route, WebsocketRoute, Any]) -> Union[Route, WebsocketRoute]:
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

    def add_router(self, router: Union[Router, Any]):
        if not isinstance(router, Router):
            fmt = 'Expected Router but got {0!r} instead'
            raise TypeError(fmt.format(router.__class__.__name__))

        for route in router:
            self.add_route(route)
        
        return router

    def get_route(self, method: str, path: str) -> Optional[Union[Route, WebsocketRoute]]:
        res = (path, method)
        route = self.router.routes.get(res)

        return route

    def get(self, path: str) -> Callable[[CoroFunc], Route]:
        def decorator(func: CoroFunc) -> Route:
            route = Route(path, 'GET', func, router=self.router)
            return self.add_route(route)
        return decorator

    def put(self, path: str) -> Callable[[CoroFunc], Route]:
        def decorator(func: CoroFunc):
            route = Route(path, 'PUT', func, router=self.router)
            return self.add_route(route)
        return decorator

    def post(self, path: str) -> Callable[[CoroFunc], Route]:
        def decorator(func: CoroFunc):
            route = Route(path, 'POST', func, router=self.router)
            return self.add_route(route)
        return decorator

    def delete(self, path: str) -> Callable[[CoroFunc], Route]:
        def decorator(func: CoroFunc):
            route = Route(path, 'DELETE', func, router=self.router)
            return self.add_route(route)
        return decorator

    def head(self, path: str) -> Callable[[CoroFunc], Route]:
        def decorator(func: CoroFunc):
            route = Route(path, 'HEAD', func, router=self.router)
            return self.add_route(route)
        return decorator

    def options(self, path: str) -> Callable[[CoroFunc], Route]:
        def decorator(func: CoroFunc):
            route = Route(path, 'OPTIONS', func, router=self.router)
            return self.add_route(route)
        return decorator

    def patch(self, path: str) -> Callable[[CoroFunc], Route]:
        def decorator(func: CoroFunc):
            route = Route(path, 'PATCH', func, router=self.router)
            return self.add_route(route)
        return decorator

    def remove_route(self, route: Union[Route, WebsocketRoute]):
        self.router.routes.pop((route.path, route.method))
        return route

    def add_event_listener(self, coro: CoroFunc, name: Optional[str]=None):
        if not inspect.iscoroutinefunction(coro):
            raise RegistrationError('Listeners must be coroutines')

        actual = name if name else coro.__name__

        if actual in self._listeners.keys():
            self._listeners[actual].append(coro)
            return Listener(coro, actual)

        self._listeners[actual] = [coro]
        return Listener(coro, actual)

    def event(self, name: Optional[str]=None) -> Callable[[CoroFunc], Listener]:
        def decorator(func: CoroFunc):
            return self.add_event_listener(func, name)
        return decorator

    def dispatch(self, name: str, *args: Any, **kwargs: Any):
        loop = self.loop
        if not loop:
            return

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

        tasks = [loop.create_task(listener(*args, **kwargs), name=f'Event-{name}') for listener in listeners]
        self._active_listeners.extend(tasks)

    def get_view(self, path: str):
        return self._views.get(path)

    def register_view(self, view: Union[HTTPView, Any]):
        if not isinstance(view, HTTPView):
            raise RegistrationError('Expected HTTPView but got {0!r} instead.'.format(view.__class__.__name__))

        view.as_routes(router=self.router)
        self._views[view.__url_route__] = view

        return view

    def view(self, path: str):
        def decorator(cls: Type[HTTPView]):
            if cls.__url_route__ == '':
                cls.__url_route__ = path

            view = cls()
            return self.register_view(view)
        return decorator

    def middleware(self, func: CoroFunc) -> CoroFunc:
        if not inspect.iscoroutinefunction(func):
            raise RegistrationError('Middlewares must be coroutines')

        self._middlewares.append(func)
        return func

    async def on_error(self, 
                    route: Union[Route, PartialRoute], 
                    request: Request,
                    worker: Worker, 
                    exception: Exception):
        traceback.print_exception(type(exception), exception, exception.__traceback__)

async def run(app: Application):
    try:
        await app.start()
        loop = app.loop

        if not loop:
            loop = compat.get_running_loop()
        
        fut = loop.create_future()
        await fut
    finally:
        await app.close()

    return app