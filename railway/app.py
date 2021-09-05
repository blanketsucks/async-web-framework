import datetime
import functools
import ssl
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Type, Union
import pathlib
import re
import inspect
import logging
import multiprocessing
import socket
import asyncio
import traceback

from ._types import CoroFunc
from .resources import Resource
from . import compat, utils
from .server import ClientConnection
from .request import Request
from .responses import NotFound, MethodNotAllowed
from .errors import *
from .router import Router
from .settings import Settings
from .objects import PartialRoute, Route, Listener, WebsocketRoute, Middleware
from .injectables import Injectable, InjectableMeta
from .views import HTTPView
from .response import Response, JSONResponse, FileResponse, HTMLResponse
from .file import File
from .websockets import ServerWebsocket as Websocket
from .workers import Worker
from .models import Model

log = logging.getLogger(__name__)

__all__ = (
    'dualstack_ipv6',
    'Application',
)


class Application(Injectable, metaclass=InjectableMeta):
    """
    A class respreseting an ASGI application.

    Attributes:
        host: A string representing the host to listen on.
        port: An integer representing the port to listen on.
        url_prefix: A string representing the url prefix.
        router: A [Router](./router.md) instance.
        settings: A [Settings](./settings.md) instance.
        worker_count: An integer representing the number of workers to spawn.
        suppress_warnings: A bool indicating whether warnings should be surpressed.
        ssl_context: A `ssl.SSLContext` instance.
    """
    def __init__(self,
                host: Optional[str]=None,
                port: Optional[int]=None,
                url_prefix: Optional[str]=None, 
                *,
                loop: Optional[asyncio.AbstractEventLoop]=None,
                ipv6: bool=False,
                sock: Optional[socket.socket]=None,
                worker_count: Optional[int]=None, 
                settings_file: Optional[Union[str, pathlib.Path]]=None, 
                load_settings_from_env: Optional[bool]=None,
                suppress_warnings: Optional[bool]=False,
                use_ssl: Optional[bool]=False,
                ssl_context: Optional[ssl.SSLContext]=None):
        """
        Constructor.

        Args:
            host: A string representing the host to listen on.
            port: An integer representing the port to listen on.
            url_prefix: A string representing the url prefix.
            ipv6: A bool indicating whether to use ipv6.
            sock: A `socket.socket` instance to use instead of creating a new one.
            worker_count: An integer representing the number of workers to spawn.
            settings_file: A string representing the path to a settings file.
            load_settings_from_env: A bool indicating whether to load settings from the environment.
            suppress_warnings: A bool indicating whether to suppress warnings.
            use_ssl: A bool indicating whether to use ssl.
            ssl_context: A `ssl.SSLContext` instance.
        """
        if ipv6:
            has_ipv6 = utils.has_ipv6()
            if not has_ipv6:
                raise RuntimeError('IPv6 is not supported')

        self.host: str = utils.validate_ip(host, ipv6=ipv6)
        self.port: int = port or 8080
        self._ipv6 = ipv6
        self.url_prefix: str = url_prefix or ''
        self.router: Router = Router(self.url_prefix)
        self.settings: Settings = Settings()
        if worker_count is None:
            worker_count = (multiprocessing.cpu_count() * 2) + 1

        self.worker_count: int = worker_count
        self.suppress_warnings: bool = suppress_warnings
        self._use_ssl = use_ssl
        self.ssl_context: ssl.SSLContext = ssl_context

        if self._use_ssl and self.ssl_context is None:
            self.ssl_context = ssl.create_default_context()
            self.ssl_context.check_hostname = False

        if settings_file is not None:
            self.settings = Settings.from_file(settings_file)

        if load_settings_from_env is True:
            self.settings = Settings.from_env_vars()

        self._listeners: Dict[str, List[Listener]] = {}
        self._resources: Dict[str, Resource] = {}
        self._views: Dict[str, HTTPView] = {}
        self._middlewares: List[Middleware] = []
        self._active_listeners: List[asyncio.Task[Any]] = []
        self._websocket_tasks: List[asyncio.Task[Any]] = []
        self._worker_tasks: List[asyncio.Task[None]] = []
        self._loop = loop or compat.get_event_loop()
        self._closed = False

        if sock:
            if not isinstance(sock, socket.socket):
                raise TypeError('sock must be a socket.socket instance')

            val = sock.getsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR)
            if not val:
                raise RuntimeError('socket does not have SO_REUSEADDR enabled')

        self._socket = sock or (
            self._make_ipv6_socket(self.host, self.port) if self._ipv6 
            else self._make_ipv4_socket(self.host, self.port)
        )
        self._workers = self._add_workers()

        self.inject(self)

    def __repr__(self) -> str:
        """
        Returns:
            A string representation of this instance.
        """
        prefix = self.url_prefix or '/'
        return f'<Application url_prefix={prefix!r} is_closed={self.is_closed()}>'

    async def __aenter__(self):
        """
        A context manager that starts the application and closes it accordingly.

        Returns:
            The same `Application` instance.
        """
        self.start()
        return self
    
    async def __aexit__(self, *args: Any):
        await self.close()
        return self

    def _log(self, message: str):
        log.info(message)

    def _build_url(self, path: str, is_websocket: bool=False) -> str:
        if path not in self.paths:
            raise ValueError(f'Path {path!r} does not exist')

        if self.is_ipv6():
            return path

        scheme = 'ws' if is_websocket else 'http'

        base = f'{scheme}://{self.host}:{self.port}'
        return base + path

    def _add_workers(self):
        workers: Dict[int, Worker] = {}

        for i in range(self.worker_count):
            worker = Worker(self, i)
            workers[worker.id] = worker
        
        return workers

    def _make_ipv6_socket(self, host: str, port: int):
        sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        sock.bind((host, port))
        return sock

    def _make_ipv4_socket(self, host: str, port: int):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        sock.bind((host, port))
        return sock

    def _ensure_listeners(self):
        for task in self._active_listeners:
            if task.done():
                self._active_listeners.remove(task)

    def _ensure_websockets(self):
        for ws in self._websocket_tasks:
            if ws.done():
                self._websocket_tasks.remove(ws)

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
        """
        Parses a response to a usable `Response` instance.

        Args:
            response: A response to be parsed.

        Returns:
            A usable `Response` instance.

        Raises:
            ValueError: If the response is not parsable.
        
        """
        status = 200

        if isinstance(response, tuple):
            response, status = response

            if not isinstance(status, int):
                raise TypeError('Response status must be an integer.')

            status = self._validate_status_code(status)

        if isinstance(response, File):
            response = FileResponse(response, status=status)  

        elif isinstance(response, Response):
            if isinstance(response, FileResponse):
                await response.read()
                response.file.close()

            return response

        if isinstance(response, Model):
            resp = JSONResponse(response.json(), status=status)
            return resp

        if isinstance(response, str):
            resp = HTMLResponse(response, status=status)
            return resp

        if isinstance(response, (dict, list)):
            resp = JSONResponse(response, status=status)
            return resp

        raise ValueError(f'Could not parse response {response!r}')

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

        self._websocket_tasks.append(task)
        self._ensure_websockets()

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

            resp = await utils.maybe_coroutine(route.callback, request, **kwargs)
        except Exception as exc:
            if not route:
                route = PartialRoute(
                    path=request.url.path,
                    method=request.method
                )

            self.dispatch('error', route, request, worker, exc)
            return

        resp = await request.send(resp)

        if route._after_request:
            await utils.maybe_coroutine(route._after_request, request, resp, **kwargs)

    @property
    def workers(self) -> List[Worker]:
        """
        Returns:
            A list of all workers.
        """
        return list(self._workers.values())

    @property
    def views(self) -> List[HTTPView]:
        """
        Returns:
            A list of all views.
        """
        return list(self._views.values())

    @property
    def socket(self) -> socket.socket:
        """
        Returns:
            The `socket.socket` instance used by the application.
        """
        return self._socket

    @property
    def middlewares(self) -> List[Middleware]:
        """
        Returns:
            A list of all registered middlewares.
        """
        return self._middlewares

    @property
    def listeners(self) -> List[Listener]:
        """
        Returns:
            A list of all registered listeners.
        """
        return list(self._listeners.values())

    @property
    def resources(self) -> List[Resource]:
        """
        Returns:
            A list of all registered resources.
        """
        return list(self._resources.values())

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        """
        Returns:
            The event loop used by the application.
        """
        return self._loop

    @loop.setter
    def setter(self, value):
        if not isinstance(value, asyncio.AbstractEventLoop):
            raise TypeError('loop must be an instance of asyncio.AbstractEventLoop')

        self._loop = value

    @property
    def urls(self) -> Set[str]:
        """
        Returns:
            A set of all registered URLs.
        """
        return {
            self._build_url(route.path, is_websocket=isinstance(route, WebsocketRoute)) 
            for route in self.router
        }

    @property
    def paths(self) -> Set[str]:
        """
        Returns:
            A set of all registered paths.
        """
        return {route.path for route in self.router}

    def url_for(self, path: str, *, is_websocket: bool=False, **kwargs) -> str:
        """
        Builds a URL for a given path.

        Args:
            path: The path to build a URL for.
            is_websocket: Whether the path is a websocket path.
            **kwargs: Additional arguments to build the URL.
        
        Returns:
            The built URL.

        Raises:
            ValueError: If the path is not a valid one.
        
        """
        return self._build_url(path.format(**kwargs), is_websocket=is_websocket)

    def inject(self, obj: Injectable):
        """
        Applies the given object's routes, listeners and middlewares to the application.

        Args:
            obj: The object to inject.

        Raises:
            TypeError: If the object is not an instance of `Injectable`.   
        """

        if not isinstance(obj, Injectable):
            raise TypeError('obj must be an Injectable')

        for route in obj.__routes__:
            route.callback = functools.partial(route.callback, obj)

            if route._after_request:
                route._after_request = functools.partial(route._after_request, obj)

            for middleware in route.middlewares:
                middleware.callback = functools.partial(middleware.callback, obj)

            self.add_route(route)

        for listener in obj.__listeners__:
            listener.callback = functools.partial(listener.callback, obj)
            self.add_event_listener(listener.callback, listener.event)
        
        for middleware in obj.__middlewares__:
            middleware.callback = functools.partial(middleware.callback, obj)
            self.add_middleware(middleware.callback)

        return self

    def eject(self, obj: Injectable):

        if not isinstance(obj, Injectable):
            raise TypeError('obj must be an Injectable')

        for route in obj.__routes__:
            self.remove_route(route)

        for listener in obj.__listeners__:
            self.remove_event_listener(listener)

        for middleware in obj.__middlewares__:
            self.remove_middleware(middleware)

        return self
    
    def is_closed(self) -> bool:
        """
        Whether or not the application has been closed.

        Returns:
            True if the application has been closed, False otherwise.

        """
        return self._closed

    def is_serving(self) -> bool:
        """
        Whether or not the application is serving requests.

        Returns:
            True if the application is serving requests, False otherwise.
        """
        return all([worker.is_serving() for worker in self.workers])

    def is_ipv6(self) -> bool:
        """
        Wheter or not the application is serving IPv6 requests.

        Returns:
            True if the application is serving IPv6 requests, False otherwise.
        """
        return self._ipv6 and utils.is_ipv6(self.host)

    def is_ssl(self) -> bool:
        """
        Whether or not the application is serving SSL requests.

        Returns:
            True if the application is serving SSL requests, False otherwise.
        """
        return self._use_ssl and isinstance(self.ssl_context, ssl.SSLContext)

    def get_worker(self, id: int) -> Optional[Worker]:
        """
        Returns the worker with the given ID.

        Args:
            id: The ID of the worker to return.

        Returns:
            The worker with the given ID, or None if no worker with the given ID exists.
        """
        return self._workers.get(id)

    def add_worker(self, worker: Union[Worker, Any]) -> Worker:
        """
        Adds a worker to the application.

        Args:
            worker: The worker to add.

        Returns:
            The worker that was added.

        Raises:
            TypeError: If the worker is not an instance of `Worker`.
            ValueError: If the worker already exists.
        """
        if not isinstance(worker, Worker):
            raise TypeError('worker must be an instance of Worker')

        if worker.id in self._workers:
            raise ValueError(f'Worker with id {worker.id} already exists')

        self._workers[worker.id] = worker
        return worker

    def start(self):
        """
        Starts the application.
        """
        loop = self.loop

        for worker in self.workers:
            task = loop.create_task(worker.run(loop), name=f'Worker-{worker.id}')
            self._worker_tasks.append(task)

        self.dispatch('startup')

    def run(self):
        """
        Starts the application but blocks until the application is closed.
        """
        loop = self.loop
        self.start()

        try:
            loop.run_forever()
        except KeyboardInterrupt:
            loop.run_until_complete(self.close())
            loop.stop()

        return self

    async def close(self):
        """
        Closes the application.
        """
        for task in self._worker_tasks:
            task.cancel()

        for worker in self.workers:
            await worker.stop()

        self._closed = True

        self.dispatch('shutdown')
        log.info(f'[Application] Closed application.')

    def websocket(self, path: str) -> Callable[[CoroFunc], WebsocketRoute]:
        """
        Registers a websocket route.

        Args:
            path: The path to register the route for.
        """
        def decorator(coro: CoroFunc) -> WebsocketRoute:
            route = WebsocketRoute(path, 'GET', coro, router=self.router)
            self.add_route(route)

            return route
        return decorator

    def route(self, path: str, method: Optional[str]=None) -> Callable[[CoroFunc], Route]:
        """
        Registers a route.

        Args:
            path: The path to register the route for.
            method: The HTTP method to register the route for.
        """
        actual = method or 'GET'

        def decorator(func: CoroFunc) -> Route:
            route = Route(path, actual, func, router=self.router)
            return self.add_route(route)
        return decorator

    def add_route(self, route: Union[Route, WebsocketRoute, Any]) -> Union[Route, WebsocketRoute]:
        """
        Adds a route to the application.

        Args:
            route: The `Route` instance to add.

        Returns:
            The route that was added.

        Raises:
            RegistrationError: If the route already exists or the argument passed in was not an instance of either `Route` or `WebsocketRoute`.
        """
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

    def add_router(self, router: Union[Router, Any]) -> Router:
        """
        Applies a router's routes and middlewares to the application.

        Args:
            router: The `Router` to apply.

        Returns:
            The router that was added.

        Raises:
            TypeError: If the router is not an instance of `Router`.

        """

        if not isinstance(router, Router):
            fmt = 'Expected Router but got {0!r} instead'
            raise TypeError(fmt.format(router.__class__.__name__))

        for route in router:
            self.add_route(route)

        for middleware in router.middlewares:
            self.add_middleware(middleware)
        
        return router

    def get_route(self, method: str, path: str) -> Optional[Union[Route, WebsocketRoute]]:
        """
        Gets a route from the application.

        Args:
            method: The HTTP method to get the route for.
            path: The path to get the route for.

        Returns:
            The route that was found.
        """
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

    def remove_route(self, route: Union[Route, WebsocketRoute]) -> Union[Route, WebsocketRoute]:
        """
        Removes a route from the application.
        
        Args:
            route: The route to remove.

        Returns:
            The route that was removed.
        """
        self.router.routes.pop((route.path, route.method))
        return route

    def add_event_listener(self, coro: CoroFunc, name: Optional[str]=None) -> Listener: 
        """
        Adds an event listener to the application.

        Args:
            coro: The coroutine function to add as an event listener.
            name: The name of the event to listen for.

        Returns:
            The event listener that was added.

        Raises:
            RegistrationError: If the `coro` argument that was passed in is not a proper coroutine function.
        """
        if not inspect.iscoroutinefunction(coro):
            raise RegistrationError('Listeners must be coroutines')

        actual = name if name else coro.__name__
        listener = Listener(coro, actual)

        if actual in self._listeners.keys():
            self._listeners[actual].append(listener)
            return listener

        self._listeners[actual] = [listener]
        return listener

    def remove_event_listener(self, listener: Listener) -> Listener:
        """
        Removes a listener from the application.

        Args:
            listener: The listener to remove.

        Returns:
            The listener that was removed.
        """
        self._listeners[listener.event].remove(listener)
        return listener

    def event(self, name: Optional[str]=None) -> Callable[[CoroFunc], Listener]:
        """
        A decorator that adds an event listener to the application.

        Args:
            name: The name of the event to listen for, if nothing was passed in the name of the function is used.
        """
        def decorator(func: CoroFunc):
            return self.add_event_listener(func, name)
        return decorator

    def dispatch(self, name: str, *args: Any, **kwargs: Any):
        loop = self.loop
        if not loop:
            return

        log.debug(f'[Application] Dispatching event: {name!r}.')

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

    def add_view(self, view: Union[HTTPView, Any]):
        if not isinstance(view, HTTPView):
            raise RegistrationError('Expected HTTPView but got {0!r} instead.'.format(view.__class__.__name__))

        view.as_routes(router=self.router)
        self._views[view.__url_route__] = view

        return view

    def remove_view(self, path: str) -> Optional[HTTPView]:
        view = self._views.pop(path, None)
        if not view:
            return None

        view.as_routes(router=self.router, remove_routes=True)
        return view

    def get_view(self, path: str):
        return self._views.get(path)

    def view(self, path: str):
        def decorator(cls: Type[HTTPView]):
            if not cls.__url_route__:
                cls.__url_route__ = path

            view = cls()
            return self.add_view(view)
        return decorator

    def add_resource(self, resource: Union[Resource, Any]) -> Resource:
        if not isinstance(resource, Resource):
            raise RegistrationError('Expected Resource but got {0!r} instead.'.format(resource.__class__.__name__))

        self.inject(resource)
        self._resources[resource.name] = resource

        return resource

    def remove_resource(self, name: str) -> Optional[Resource]:
        resource = self._resources.pop(name, None)
        if not resource:
            return None

        self.eject(resource)
        return resource

    def get_resource(self, name: str) -> Optional[Resource]:
        return self._resources.get(name)

    def resource(self, name: str=None) -> Callable[[Type[Resource]], Resource]:
        def decorator(cls: Type[Resource]):
            resource = cls()
            if name:
                resource.name = name

            return self.add_resource(resource)
        return decorator

    def add_middleware(self, callback: CoroFunc) -> Middleware:
        middleware = Middleware(callback, router=self)
        middleware._is_global = True

        self._middlewares.append(middleware)
        return middleware
    
    def middleware(self, callback: CoroFunc) -> Middleware:
        if not inspect.iscoroutinefunction(callback):
            raise RegistrationError('Middlewares must be coroutines')

        return self.add_middleware(callback)

    def remove_middleware(self, middleware: Middleware):
        self._middlewares.remove(middleware)
        return middleware

    async def on_error(self, 
                    route: Union[Route, PartialRoute], 
                    request: Request,
                    worker: Worker, 
                    exception: Exception):
        traceback.print_exception(type(exception), exception, exception.__traceback__)
    
def dualstack_ipv6(ipv4: str=None, ipv6: str=None, *, port: int=None, **kwargs) -> Application:
    """
    Makes an application that accepts both IPv4 and IPv6 requests.

    Args:
        ipv4: The IPv4 host to use.
        ipv6: The IPv6 host to use.
        port: The port to listen on.
        kwargs: Additional arguments to pass to the Application constructor.

    Returns:
        The dual-stack application.

    Raises:
        RuntimeError: If dualstack support is not available
    """
    if not utils.has_dualstack_ipv6():
        raise RuntimeError('Dualstack support is not available')

    app = Application(worker_count=0, port=port)
    worker_count = kwargs.pop('worker_count', multiprocessing.cpu_count() + 1)

    ipv4 = utils.validate_ip(ipv4)
    ipv6 = utils.validate_ip(ipv6, ipv6=True)

    ipv4_socket = app._make_ipv4_socket(ipv4, app.port)
    ipv6_socket = app._make_ipv6_socket(ipv6, app.port)

    workers = []
    id: int = 0

    for i in range(worker_count):
        worker = Worker(app, id)
        worker.socket = ipv4_socket

        workers.append(worker)
        id += 1

    for i in range(worker_count):
        id += 1

        worker = Worker(app, id)
        worker.socket = ipv6_socket

        workers.append(worker)

    for worker in workers:
        app.add_worker(worker)

    app.worker_count = len(workers)
    return app

