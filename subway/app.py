from __future__ import annotations

from typing import Any, Callable, Dict, List, Literal, Optional, Set, Type, TypeVar, Union, AsyncIterator
import datetime
import os
import sys
import ssl
import inspect
import logging
import socket
import uuid
import asyncio
import traceback
import jinja2
import pathlib
import types

from .types import (
    Coro,
    CoroFunc,
    MaybeCoro,
    StatusCodeCallback,
    RouteResponse,
    ResponseStatus,
    ResponseMiddleware,
    CookieSessionCallback
)
from .resources import Resource
from . import compat, utils
from .request import Request
from .responses import redirects, HTTPException, InternalServerError
from .errors import *
from .router import Router, ResolvedRoute
from .settings import Settings, Config
from .objects import PartialRoute, Route, Listener, WebSocketRoute, Middleware
from .views import HTTPView
from .response import Response, JSONResponse, FileResponse, HTMLResponse, StreamResponse
from .files import File
from .websockets import ServerWebSocket as WebSocket, WebSocketProtocol
from .workers import Worker
from .models import Model, IncompatibleType, MissingField
from .url import URL
from .base import BaseApplication
from .blueprints import Blueprint
from .converters import AbstractConverter
from .cookies import Cookie

log = logging.getLogger(__name__)

T = TypeVar('T')

__all__ = (
    'Application',
)

class Application(BaseApplication):
    """
    A class representing an application.

    Parameters
    ----------
    host: :class:`str`
        A string representing the host to listen on.
    port: :class:`int`
        An integer representing the port to listen on.
    path: :class:`str`
        A string representing the path to a UNIX socket.
    url_prefix: :class:`str`
        A string representing the url prefix.
    loop: :class:`asyncio.AbstractEventLoop`
        An optional asyncio event loop.
    templates_dir: :class:`str`
        A string representing the path to the templates directory used for rendering templates.
    settings: :class:`~.Settings`
        An optional :class:`~.Settings` instance. If not specified, the default settings will be used.
    settings_file: Union[:class:`pathlib.Path`, :class:`str`]
        An optional path to a settings file.
    load_settings_from_env: :class:`bool`
        An optional bool indicating whether to load settings from the environment.
    ipv6: :class:`bool`
        An optional bool indicating whether to use IPv6.
    sock: :class:`socket.socket`
        An optional :class:`socket.socket` instance.
    worker_count: :class:`int`
        An optional integer representing the number of workers to spawn.
    ssl: :class:`bool`
        An optional bool indicating whether to use SSL.
    ssl_context: :class:`ssl.SSLContext`
        An optional :class:`ssl.SSLContext` instance.
    cookie_session_callback: Callable[[:class:`~.Request`, :class:`~.Response`], Any]
        A callback that gets called whenever there is a need to generate a cookie header value
        for responses. This function must return a single value being a string, bytes or a :class:`~.Cookie` object
        anything else will raise an error. Rhe default for this is a lambda function
        that returns a :attr:`uuid.UUID.hex` value.
    backlog: :class:`int`
        An integer representing the backlog that gets passed to the :meth:`socket.socket.listen` method.
        Defaults to 200.
    reuse_host: :class:`bool`
        An optional bool indicating whether to reuse the host. If set to ``False`` the number of worker used will be at 1 to
        avoid issues with the host being reused.
    reuse_port: :class:`bool`
        An optional bool indicating whether to reuse the port.
    connection_read_timeout: :class:`float`
        An optional integer representing the connection read timeout.

    Raises
    ------
    RuntimeError
        If ``ipv6`` was specified and the system does not support it,
        or ``sock`` was specified and the socket does not have ``SO_REUSEADDR`` enabled.
    TypeError
        If ``port`` is not a valid integer. This can from either the constructor or the settings,
        if ``worker_count`` is not a valid integer, or
        if ``sock`` was specified, and it is not a valid :class:`socket.socket` instance.
    ValueError
        If ``host`` is not a valid IP. This can from either the constructor or the settings, or
        if ``worker_count`` is an integer less than 0.

    Attributes
    -----------
    host: :class:`str`
        A string representing the host to listen on.
    port: :class:`int`
        An integer representing the port to listen on.
    url_prefix: :class:`str`
        A string representing the url prefix.
    router: :class:`~subway.Router`
        The router used for registering routes.
    settings: :class:`~.Settings`.
        The settings used to configure the application.
    worker_count: :class:`int` 
        An integer representing the number of workers to spawn.
    ssl_context: :class:`ssl.SSLContext`
        A `ssl.SSLContext` instance.
    cookie_session_callback: Callable[[:class:`~.Request`, :class:`~.Response`], Any]
        A callback that gets called whenever there is a need to generate a cookie header value for responses.
    config: :class:`dict`
        A dict letting users store custom configuration.
    """
    RESPONSE_HANDLERS: Dict[Type[Any], Callable[[Application, Any], MaybeCoro[Response]]] = {
        str: lambda _, body: HTMLResponse(body),
        bytes: lambda _, body: Response(body),   
        dict: lambda _, body: JSONResponse(body),
        list: lambda _, body: JSONResponse(body),
        Response: lambda _, body: body,
        File: lambda _, body: FileResponse(body),
        types.AsyncGeneratorType: lambda _, body: StreamResponse(body),
        Model: lambda _, model: JSONResponse(model.json()),
    }

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        path: Optional[str] = None,
        url_prefix: Optional[str] = None,
        *,
        templates_dir: str = '/templates',
        loop: Optional[asyncio.AbstractEventLoop] = None,
        settings: Optional[Settings] = None,
        settings_file: Optional[Union[str, os.PathLike[str]]] = None,
        load_settings_from_env: bool = False,
        ipv6: bool = False,
        sock: Optional[socket.socket] = None,
        worker_count: Optional[int] = None,
        ssl: bool = False,
        ssl_context: Optional[ssl.SSLContext] = None,
        cookie_session_callback: Optional[CookieSessionCallback] = None,
        backlog: Optional[int] = None,
        reuse_host: bool = True,
        reuse_port: bool = False,
        connection_read_timeout: float = 5.0,
    ) -> None:
        self._ipv6 = ipv6
        if ipv6 and host is None:
            host = utils.LOCALHOST_V6

        self.settings = self.load_settings(settings, settings_file, load_settings_from_env)
        host = host or self.settings.host
        port = port or self.settings.port

        assert host is not None, 'host is required'
        self.host = utils.validate_ip(host, ipv6=ipv6)
        self.port = port
        self.path = path
        self.url_prefix = url_prefix or self.settings.url_prefix
        self.router = Router(self.url_prefix)
        self.ssl_context = ssl_context or self.settings.ssl_context
        self.worker_count = self.settings.worker_count if worker_count is None else worker_count
        self.connection_read_timeout = connection_read_timeout
        self.config = Config()

        if cookie_session_callback is not None:
            if not callable(cookie_session_callback):
                raise TypeError('cookie_session_callback must be a callable')

        self.cookie_session_callback = cookie_session_callback or (lambda req, res: uuid.uuid4().hex)
        self.context: Dict[str, Any] = {'url_for': self.url_for}
        self._templates_dir = templates_dir
        self._jinja_env = self.create_jinja_env()
        self._backlog = backlog or self.settings.backlog
        self._use_ssl = ssl
        self._listeners: Dict[str, List[Listener]] = {}
        self._resources: Dict[str, Resource] = {}
        self._blueprints: Dict[str, Blueprint] = {}
        self._views: Dict[str, HTTPView] = {}
        self._active_listeners: List[asyncio.Task[Any]] = []
        self._status_code_handlers: Dict[int, Callable[[Request[Application], HTTPException, Union[PartialRoute, Route]], Coro[Any]]] = {}
        self._loop = self._create_loop(loop)
        self._closed = False
        self._lifespan_tasks: List[AsyncIterator[Any]] = []
        self._reuse_host = reuse_host
        self._reuse_port = reuse_port
        self._response_middlewares: List[ResponseMiddleware] = []

        if not reuse_host:
            self.worker_count = 1

        if self._use_ssl and self.ssl_context is None:
            self.ssl_context = self.create_default_ssl_context()

        self._socket = sock
        self.setup_workers()

    async def __aenter__(self) -> 'Application':
        await self.start()
        return self

    async def __aexit__(self, *args: Any):
        await self.close()

    def _create_loop(self, loop: Optional[asyncio.AbstractEventLoop]) -> asyncio.AbstractEventLoop:
        if loop is None:
            if not compat.PY310:
                loop = compat.get_event_loop()
            else:
                try:
                    return compat.get_running_loop()
                except RuntimeError:
                    pass

                policy = compat.get_event_loop_policy()
                loop = policy.get_event_loop()

        return loop

    async def _safe_anext(self, gen: AsyncIterator[Any]) -> None:
        try:
            await gen.__anext__()
        except StopAsyncIteration:
            try:
                self._lifespan_tasks.remove(gen)
            except ValueError:
                pass

    def _find_url_from_views(self, path: str):
        view = self.get_view(path)
        if not view:
            return None

        return view.path

    def _find_url_from_resources(self, path: str):
        split = path.split('.', 1)
        if not len(split) == 2:
            return None

        name, path = split
        resource = self.get_resource(name)

        if not resource:
            raise ValueError(f'Resource {name!r} not found')

        path = f'/{path}' if not path.startswith('/') else path
        route = resource.__routes__.get(path)
        if not route:
            raise ValueError(f'Route {path!r} not found for {name!r} resource')

        return route.path

    def _find_path(self, path: str):
        if route := self._find_url_from_views(path):
            return route

        if route := self._find_url_from_resources(path):
            return route

        return path

    def _build_url(self, path: str, is_websocket: bool = False, ignore: bool = False) -> URL:
        real = self._find_path(path)

        if real not in self.paths:
            if not ignore:
                raise ValueError(f'Path {path!r} does not exist')

        scheme = 'ws' if is_websocket else 'http'
        if self.is_ssl():
            scheme += 's'

        if self.is_ipv6():
            base = f'{scheme}://[{self.host}]:{self.port}'
        else:
            base = f'{scheme}://{self.host}:{self.port}'

        return URL(base + real)

    def _create_workers(self):
        workers: Dict[int, Worker] = {}

        for i in range(self.worker_count):
            worker = Worker(self, i)
            workers[worker.id] = worker

        return workers

    async def _transform_model(self, parameter: Parameter, request: Request[Application]) -> Any:
        try:
            data = await request.json(check_content_type=True)
        except AssertionError:
            if parameter.default is not parameter.empty:
                return parameter.default

            raise
        
        annotations = utils.get_union_args(parameter.annotation)

        for annotation in annotations:
            if issubclass(annotation, Model):
                try:
                    return annotation.from_json(data)
                except (IncompatibleType, MissingField):
                    continue

        if parameter.default is not parameter.empty:
            return parameter.default

        raise BadModelConversion(data, parameter, annotations)

    async def _transform(
        self, 
        parameter: Parameter, 
        argument: str, 
        request: Request[Application]
    ) -> Any:
        annotation = parameter.annotation

        if getattr(annotation, '__origin__', None) is Literal:
            if argument not in annotation.__args__:
                if parameter.default is not parameter.empty:
                    return parameter.default

                raise BadLiteralArgument(argument, parameter, annotation.__args__)

            return argument

        for annotation in utils.get_union_args(annotation):
            if isinstance(annotation, AbstractConverter):
                return await annotation.convert(request, argument)
            elif issubclass(annotation, AbstractConverter):
                return await annotation().convert(request, argument) # type: ignore

            try:
                return annotation(argument)
            except ValueError:
                continue
        
        if parameter.default is not parameter.empty:
            return parameter.default

        raise FailedConversion(argument, parameter)

    async def _convert(self, resolved: ResolvedRoute, request: Request[Application]) -> Dict[str, Any]:
        kwargs: Dict[str, Any] = {}

        route = resolved.route
        params = iter(route.signature.parameters.items())

        try:
            next(params)
        except StopIteration:
            if not route.parent:
                raise RuntimeError(f"Route {route!r} missing request argument")

            raise RuntimeError(f"Route {route!r} missing self argument")

        if route.parent:
            try:
                next(params)
            except StopIteration:
                raise RuntimeError(f"Route {route!r} missing request argument")

        if route.is_websocket():
            try:
                next(params)
            except StopIteration:
                raise RuntimeError(f"Route {route!r} missing websocket argument")

        for key, parameter in params:
            value = resolved.params.get(key)

            if value:
                if parameter.annotation is not inspect.Signature.empty:
                    value = await self._transform(parameter, value, request)
            else:
                value = await self._transform_model(parameter, request)
               
            kwargs[key] = value
            
        return kwargs

    def _validate_status_code(self, code: int):
        if 300 <= code <= 399:
            ret = 'Redirect status codes cannot be returned. Use Request.redirect instead ' \
                  'or you could return an instance of URL accompanied by the redirect status code.'
            raise ValueError(ret)

        if not (200 <= code <= 599):
            ret = f'Status code {code} is not valid'
            raise ValueError(ret)

        return code

    async def _run_request_middlewares(
        self, 
        request: Request[Application], 
        route: Route, kwargs: Dict[str, Any]
    ) -> Any:
        middlewares = route.request_middlewares.copy()
        middlewares.extend(self.request_middlewares)

        return await asyncio.gather(
            *[middleware(request, route, **kwargs) for middleware in middlewares],
        )

    async def _run_response_middlewares(
        self, 
        request: Request[Application], 
        response: Response,
        route: Route
    ) -> Any:
        middlewares = route.response_middlewares.copy()
        middlewares.extend(self.response_middlewares)

        return await asyncio.gather(
            *[middleware(request, response, route) for middleware in middlewares],
        )

    async def _handle_websocket_connection(
        self, 
        route: WebSocketRoute, 
        request: Request[Application], 
        websocket: WebSocket
    ):
        reader = request.get_reader()
        proto: Any = request.writer.get_protocol()

        protocol = WebSocketProtocol(reader, request.writer, proto.waiter)

        request.writer.set_protocol(protocol)
        await protocol.wait_until_connected()

        self.loop.create_task(route(request, websocket))

    async def _dispatch_error(
        self, 
        route: Union[PartialRoute, Route], 
        request: Request[Application], 
        exc: Exception
    ):
        if isinstance(route, Route):
            ret = await route.dispatch(request, exc)
            if ret:
                return

        if isinstance(exc, HTTPException):
            callback = self._status_code_handlers.get(exc.status)
            if callback:
                response = await callback(request, exc, route)
                await request.send(response)

                return

        listeners = self._get_listeners('on_error')
        await asyncio.gather(*[listener(request, exc, route) for listener in listeners], return_exceptions=True)

    async def _request_handler(self, request: Request[Application], websocket: Optional[WebSocket]):
        route = None

        try:
            resolved = self.router.resolve(request.url.path, request.method)
            if not resolved:
                return

            kwargs = await self._convert(resolved, request)
            ret = await self._run_request_middlewares(request=request, route=resolved.route, kwargs=kwargs)
            if not all(ret):
                return

            if resolved.route.is_websocket() and request.is_websocket():
                await self._handle_websocket_connection(resolved.route, request, websocket) # type: ignore
                return

            resp = resolved.route(request, **kwargs)
            if inspect.isawaitable(resp):
                resp = await resp

        except Exception as exc:
            if not route:
                route = PartialRoute(
                    path=request.url.path,
                    method=request.method
                )

            return await self._dispatch_error(
                route=route,
                request=request,
                exc=exc
            )

        response = await self.process_response(resp, request, resolved.route)
        
        await request.send(response, convert=False)
        await request.close()

        after_request = resolved.route._after_request # type: ignore
        if after_request:
            await utils.maybe_coroutine(after_request, request, response, **kwargs)

    def get_template(self, template: Union[str, os.PathLike[str]]) -> jinja2.Template:
        path = self.templates / template
        return self._jinja_env.get_template(str(path))

    async def render(self, path: Union[str, os.PathLike[str]], *args: Any, **kwargs: Any):
        """
        Renders a template and returns a Response object.
        The template folder if not specified in the constructor is relative to where the application was instantiated.

        Parameters
        ----------
        path: :class:`str` or :class:`os.PathLike`
            The path to the template.
        args: Any
            Positional arguments to pass to the template.
        kwargs: Any
            Keyword arguments to pass to the template.
        """
        if not self.templates.exists():
            raise RuntimeError(f'Templates folder {self.templates} does not exist')

        kwargs.update(self.context)

        template = self.get_template(path)
        body = await template.render_async(*args, **kwargs)

        return HTMLResponse(body)

    def setup_workers(self) -> None:
        self._workers = self._create_workers()

    def load_settings(
        self,
        settings: Optional[Settings],
        path: Optional[Union[str, os.PathLike[str]]],
        from_env: bool = False
    ) -> Settings:
        if settings is not None:
            return settings

        if path is not None:
            return Settings.from_file(path)
        elif from_env:
            return Settings.from_env()

        return Settings()

    def _set_socketopt(self, sock: socket.socket):
        if self.reuse_host:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        if self.reuse_port:
            if not hasattr(socket, 'SO_REUSEPORT'):
                raise RuntimeError('SO_REUSEPORT is not supported on this platform.')

            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)

    def _create_tcp_socket(self, family: socket.AddressFamily) -> socket.socket:
        if self.path is not None:
            raise ValueError('Path is not supported for TCP sockets')

        sock = socket.socket(family, socket.SOCK_STREAM, socket.IPPROTO_TCP)
        self._set_socketopt(sock)

        # sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

        # if self.ssl_context:
        #     sock = self.ssl_context.wrap_socket(sock, server_side=True)

        sock.bind((self.host, self.port))
        sock.listen(self.backlog)

        return sock

    def create_unix_socket(self) -> socket.socket:
        if not hasattr(socket, 'AF_UNIX'):
            raise RuntimeError('Unix sockets are not supported on this platform')

        if self.path is None:
            raise ValueError('Path is required for Unix sockets')

        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._set_socketopt(sock)

        # if self.ssl_context:
        #     sock = self.ssl_context.wrap_socket(sock, server_side=True)

        sock.bind(self.path)
        sock.listen(self.backlog)

        return sock

    def create_ipv6_socket(self) -> socket.socket:
        """
        Same as :meth:`create_ipv4_socket` but for IPv6, meaning it sets the socket family to ``AF_INET6``.
        """
        if not utils.has_ipv6():
            raise RuntimeError('IPv6 is not supported on this platform')

        return self._create_tcp_socket(socket.AF_INET6)

    def create_ipv4_socket(self) -> socket.socket:
        """
        Creates a :class:`socket.socket` with the :const:`socket.AF_INET` family and the :const:`socket.SOCK_STREAM` type.
        """
        return self._create_tcp_socket(socket.AF_INET)

    def create_socket(self) -> socket.socket:
        if self.path is not None:
            sock = self.create_unix_socket()
        elif self._ipv6:
            sock = self.create_ipv6_socket()
        else:
            sock = self.create_ipv4_socket()

        sock.setblocking(False)
        return sock

    def create_default_ssl_context(self) -> ssl.SSLContext:
        """
        Creates a default ssl context.
        """
        context = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)
        return context

    def create_jinja_env(self) -> jinja2.Environment:
        """
        Creates a default jinja2 environment.
        """
        loader = jinja2.FileSystemLoader(str(self.templates))
        env = jinja2.Environment(loader=loader, enable_async=True)

        return env

    async def parse_response(self, response: RouteResponse) -> Response:
        """
        Parses a response to a usable ``Response`` instance.

        Parameters
        ----------
        response: Any
            A response to be parsed.

        Raises
        ------
            ValueError: If the response is not parsable.
        """
        status = 200
        resp = None

        if isinstance(response, tuple):
            response, status = response

            if not isinstance(status, int):
                raise TypeError('Response status must be an integer')

            if isinstance(response, URL):
                if not 300 <= status <= 399:
                    ret = f'{status!r} is not a valid redirect status code'
                    raise ValueError(ret)

                cls = redirects[status]
                return cls(location=str(response))

            else:
                status = self._validate_status_code(status)

        cls = type(response)
        callback = self.RESPONSE_HANDLERS.get(cls)

        if callback is None:
            raise ValueError(f'Could not parse {response!r} into a response')

        return await utils.maybe_coroutine(callback, self, response)

    def set_default_session_cookie(self, request: Request[Application], response: Response) -> Response:
        """
        Sets a cookie with the ``session_cookie_name`` of :class:`~subway.settings.Settings`.
        If the cookie already exists, do nothing.

        Parameters
        ----------
        request: :class:`~subway.Request`
            The request that was sent to the server.
        response: :class:`~subway.Response`
            The response to add the cookie to.
        """
        name = self.settings['session_cookie_name']
        cookie = request.get_default_session_cookie()

        if not cookie:
            value = self.cookie_session_callback(request, response)
            if not value:
                return response
            elif value is True:
                value = uuid.uuid4().hex

            value = value.decode() if isinstance(value, bytes) else value
            if isinstance(value, Cookie):
                response.cookies._cookies[value.name] = value
            else:
                response.add_cookie(name=name, value=value)

        return response

    def add_cache_control_header(
        self, 
        response: Response, 
        request: Request[Application], 
        route: Route
    ) -> Response:
        """
        Adds a ``Cache-Control`` header to the response.

        Parameters
        ----------
        response: :class:`~subway.Response`
            The response to add the header to.
        route: :class:`~subway.Route`
            The route that was used to generate the response.
        """
        if hasattr(route, '__cache_control__') and not response.headers.get('Cache-Control'):
            control = route.__cache_control__
            parts: List[str] = []

            for key, value in control.items():
                key = key.replace('_', '-')

                if isinstance(value, bool):
                    parts.append(key)
                else:
                    parts.append(f'{key}={value}')

            header = ', '.join(parts)
            response.headers['Cache-Control'] = header

        return response

    async def process_response(
        self, 
        resp: RouteResponse, 
        request: Request[Application], 
        route: Route
    ) -> Response:
        """
        Processes a response before it is sent to the client.

        Parameters
        ----------
        response: Any
            The response to process.
        request: :class:`~.Request`
            The request that was sent to the server.
        route: :class:`~.Route`
            The route that was used to generate the response.
        """
        response = await self.parse_response(resp)
        await self._run_response_middlewares(request, response, route)

        self.set_default_session_cookie(request, response)
        self.add_cache_control_header(response, request, route)

        if not response.headers.get('Date'):
            now = datetime.datetime.utcnow()
            response.headers['Date'] = now.strftime('%a, %d %b %Y %H:%M:%S GMT')

        if not response.headers.get('Server'):
            response.headers['Server'] = 'Subway'

        return response

    @property
    def templates(self) -> pathlib.Path[str]:
        """
        The path to the templates directory.
        """
        return pathlib.Path(self._templates_dir)

    @templates.setter
    def templates(self, value: Union[str, os.PathLike[str]]):
        self._templates_dir = str(value)

    @property
    def backlog(self) -> int:
        """
        The backlog of the server.
        """
        return self._backlog

    @backlog.setter
    def backlog(self, value: int):
        if self.is_serving():
            raise RuntimeError('Cannot change backlog while server is running')

        self._backlog = value

    @property
    def schemes(self) -> List[str]:
        """
        Returns a list of supported schemes.
        """
        schemes = ['http']
        if self.is_ssl():
            schemes.append('https')

        return schemes

    @property
    def url(self) -> URL:
        """
        Base URL of the server.
        """
        return self._build_url('/', ignore=True)

    @property
    def reuse_host(self) -> bool:
        """
        Whether to reuse the host.
        """
        return self._reuse_host

    @property
    def reuse_port(self) -> bool:
        """
        Whether to reuse the port.
        """
        return self._reuse_port

    @property
    def workers(self) -> List[Worker]:
        """
        A list of all workers.
        """
        return list(self._workers.values())

    @property
    def views(self) -> List[HTTPView]:
        """
        A list of all views.
        """
        return list(self._views.values())

    @property
    def routes(self) -> List[Route]:
        """
        A list of all routes.
        """
        return [route for route in self.router]

    @property
    def blueprints(self) -> List[Blueprint]:
        """
        A list of all blueprints.
        """
        return list(self._blueprints.values())

    @property
    def socket(self) -> Optional[socket.socket]:
        """
        The socket used to listen for connections.
        """
        return self._socket

    @socket.setter
    def socket(self, value: socket.socket):
        self._socket = value

    @property
    def request_middlewares(self) -> List[Middleware]:
        """
        A list of all request middlewares.
        """
        return self.router.request_middlewares

    @property
    def response_middlewares(self) -> List[Middleware]:
        """
        A list of all response middlewares.
        """
        return self.router.response_middlewares

    @property
    def listeners(self) -> List[Listener]:
        """
        A list of all listeners.
        """
        return list(*self._listeners.values())

    @property
    def resources(self) -> List[Resource]:
        """
        A list of all resources.
        """
        return list(self._resources.values())

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        """
        The event loop used by the application.
        """
        return self._loop

    @loop.setter
    def loop(self, value: asyncio.AbstractEventLoop):
        if not isinstance(value, asyncio.AbstractEventLoop):
            raise TypeError('loop must be an instance of asyncio.AbstractEventLoop')

        self._loop = value

    @property
    def urls(self) -> Set[URL]:
        """
        A set of all URLs.
        """
        return {
            self._build_url(route.path, is_websocket=isinstance(route, WebSocketRoute))
            for route in self.router
        }

    @property
    def paths(self) -> Set[str]:
        """
        A set of all paths.
        """
        return {route.path for route in self.router}

    def url_for(self, path: str, *, is_websocket: bool = False, **kwargs: Any) -> URL:
        """
        Builds a URL for a given path and returns it.

        Parameters
        ----------
        path: :class:`str`
            The path to build a URL for.
        is_websocket: :class:`bool`
            Whether the path is a websocket path.
        **kwargs: 
            Additional arguments to build the URL.
        """
        url = self._build_url(path.format(**kwargs), is_websocket=is_websocket)
        return url

    def is_closed(self) -> bool:
        """
        Returns whether or not the application has been closed.
        """
        return self._closed

    def is_serving(self) -> bool:
        """
        Returns whether or not the application is serving requests.
        """
        return all([worker.is_serving() for worker in self.workers])

    def is_ipv6(self) -> bool:
        """
        Returns wheter or not the application is serving IPv6 requests.
        """
        return self._ipv6 and utils.is_ipv6(self.host)

    def is_ssl(self) -> bool:
        """
        Returns whether or not the application is serving SSL requests.
        """
        return self._use_ssl is True and isinstance(self.ssl_context, ssl.SSLContext)

    def add_worker(self, worker: Worker) -> Worker:
        """
        Adds a worker to the application.

        Parameters
        ----------
        worker: :class:`~.Worker`
            The worker to add.

        Raises
        ------
        TypeError: 
            If the worker is not an instance of :class:`~.Worker:.
        ValueError:
            If the worker already exists.
        """
        if not isinstance(worker, Worker):
            raise TypeError('worker must be an instance of Worker')

        if worker.id in self._workers:
            raise ValueError(f'Worker with id {worker.id} already exists')

        self._workers[worker.id] = worker
        return worker

    def _cancel_all_tasks(self) -> None:
        to_cancel = asyncio.all_tasks(self.loop)
        if not to_cancel:
            return

        for task in to_cancel:
            task.cancel()

        self.loop.run_until_complete(
            future=asyncio.gather(*to_cancel, loop=self.loop, return_exceptions=True)
        )

        for task in to_cancel:
            if task.cancelled():
                continue
            if task.exception() is not None:
                self.loop.call_exception_handler({
                    'message': 'unhandled exception during Application shutdown',
                    'exception': task.exception(),
                    'task': task,
                })

    async def wait_until_ready(self) -> None:
        """
        Waits until the application is ready.
        """
        await asyncio.gather(*[worker.wait_until_ready() for worker in self.workers])

    async def start(self) -> None:
        """
        Starts the application.
        """
        if not self.socket or utils.socket_is_closed(self.socket):
            self._socket = self.create_socket()

        if self.is_serving():
            raise RuntimeError('Application is already serving requests')

        if self.is_closed():
            raise RuntimeError('Application is closed')

        if not self.workers:
            raise ValueError('No workers have been added to the application')

        for worker in self.workers:
            await worker.serve()

        for generator in self._lifespan_tasks:
            await self._safe_anext(generator)

        self.dispatch('startup')

    def run(self) -> None:
        """
        Starts the application but blocks until the application is closed.
        """
        loop = self.loop
        self.loop.run_until_complete(self.start())

        try:
            loop.run_forever()
        except (KeyboardInterrupt, OSError):
            if not self.is_closed():
                loop.run_until_complete(self.close())

        # try:
        #     self._cancel_all_tasks()
        #     loop.run_until_complete(loop.shutdown_asyncgens())
        #     loop.run_until_complete(loop.shutdown_default_executor())
        # finally:
        #     pass

    async def shutdown(self) -> None:
        """
        Closes the application with no further cleanup.
        """
        for worker in self.workers:
            await worker.close()

        for generator in self._lifespan_tasks:
            await self._safe_anext(generator)

        if self.socket and not utils.socket_is_closed(self.socket):
            self.socket.shutdown(socket.SHUT_RDWR)
            self.socket.close()
        
        self.dispatch('shutdown')

    async def close(self) -> None:
        """
        Closes the application.
        """
        if not self.is_serving():
            raise RuntimeError('Application is not running')

        if self.is_closed():
            raise RuntimeError('Application is already closed')

        await self.shutdown()

        self.clear()
        self._closed = True

        log.info(f'[Application] Closed application.')

    def clear(self) -> None:
        """
        Clears the application's internal state.
        """
        self._workers.clear()
        self._listeners.clear()
        self._lifespan_tasks.clear()

        self.router.clear()

    def lifespan(self, callback: Callable[[], AsyncIterator[Any]]) -> Callable[[], AsyncIterator[Any]]:
        """
        Adds a lifespan callback to the application.

        Parameters
        ----------
        callback: Callable
            The callback to add.
        """
        if not isinstance(callback, AsyncIterator):
            raise RegistrationError('Lifespan tasks must be async generators')

        generator = callback()
        self._lifespan_tasks.append(generator)

        return callback

    def add_router(self, router: Router) -> Router:
        """
        Applies a router's routes and middlewares to the application.

        Parameters
        ----------
        router: :class:`~subway.router.Router`
            The router to apply.

        Raises
        ----------
        TypeError: If the router is not an instance of `Router`.

        Example
        ----------

        .. code-block:: python3

            import subway

            app = subway.Application()
            router = subway.Router()

            @router.route('/hi', 'GET')
            async def hi(request: subway.Request):
                return 'hi'

            app.add_router(router)
            app.run()

        """
        if not isinstance(router, Router):
            fmt = 'Expected Router but got {0!r} instead'
            raise TypeError(fmt.format(router.__class__.__name__))

        self.router.union(router)
        return router

    def register_response_handler(
        self, 
        type: Type[T], 
        callback: Callable[[Application, T], Response]
    ) -> None:
        """
        Registers a response handler for a given type.
        
        Parameters
        ----------
        type: :class:`type`
            The type to register the handler for.
        callback: Callable
            The callback to register.
        """
        self.RESPONSE_HANDLERS[type] = callback

    def add_event_listener(self, callback: CoroFunc[Any], name: str) -> Listener:
        """
        Adds an event listener to the application.

        Parameters
        ----------
        callback: Callable[..., Coroutine[Any, Any, Any]]
            The coroutine function to add as an event listener.
        name: :class:`str`
            The name of the event to listen for. 
            If not given, it takes the name of the function passed in instead

        Raises
        ----------
        RegistrationError: If the ``coro`` argument that was passed in is not a proper coroutine function.
        """
        if not utils.iscoroutinefunction(callback):
            raise RegistrationError('Listeners must be coroutines')

        listener = Listener(callback, name)

        listeners = self._listeners.setdefault(name, [])
        listeners.append(listener)

        return listener

    def remove_event_listener(self, listener: Listener) -> Listener:
        """
        Removes a listener from the application.

        Parameters
        ----------
        listener: :class:`~subway.objects.Listener`
            The listener to remove.
        """
        self._listeners[listener.event].remove(listener)
        return listener

    def add_status_code_handler(
        self,
        status: ResponseStatus,
        callback: StatusCodeCallback
    ):
        """
        Adds a specific status code handler to the application.
        This applies to only error status codes for obvious reasons.

        Parameters
        ----------
        status: :class:`int`
            The status code to handle.
        callback: Callable[[:class:`~subway.objects.Request`, :class:`~subway.exceptions.HTTPException`, :class:`~subway.objects.Route`], Coro]
            The callback to handle the status code.
        """
        if not utils.iscoroutinefunction(callback):
            raise RegistrationError('Status code handlers must be coroutine functions')

        self._status_code_handlers[int(status)] = callback
        return callback

    def remove_status_code_handler(self, status: ResponseStatus):
        """
        Removes a status code handler from the application.

        Parameters
        ----------
        status: :class:`int`
            The status code to remove.
        """
        callback = self._status_code_handlers.pop(int(status), None)
        return callback

    def status_code_handler(
        self,
        status: ResponseStatus
    ) -> Callable[[StatusCodeCallback], StatusCodeCallback]:
        """
        A decorator that adds a status code handler to the application.

        Parameters
        ----------
        status: :class:`int`
            The status code to handle.

        Example
        ---------
        .. code-block :: python3

            import subway

            app = subway.Application()

            @app.status_code_handler(404)
            async def handle_404(
                request: subway.Request, 
                exception: subway.HTTPException, 
                route: subway.Route
            ):
                return {
                        'message': 'Page not found.',
                        'status': 404
                    }

            app.run()
        
        Returns
        ----------
        Any
        """
        def decorator(func: StatusCodeCallback):
            return self.add_status_code_handler(status, func)

        return decorator

    async def _run_listener(self, listener: Listener, *args: Any, **kwargs: Any):
        try:
            await listener(*args, **kwargs)
        except Exception as e:
            try:
                listeners = self._get_listeners('on_event_error')
                await asyncio.gather(*[callback(listener, e) for callback in listeners])
            except:
                pass

    def _get_listeners(self, name: str) -> List[Listener]:
        try:
            listeners = self._listeners[name]
        except KeyError:
            coro = getattr(self, name, None)
            if not coro:
                return []

            listener = Listener(callback=coro, name=name)
            listeners = [listener]

        return listeners

    def dispatch(self, name: str, *args: Any, **kwargs: Any) -> 'asyncio.Future[Any]':
        """
        Dispatches an event.

        Example
        ---------

        .. code-block :: python3

            app = Application()

            @app.event('on_my_event')
            async def my_event(*args, **kwargs):
                print('Event fired')

            app.dispatch('my_event')
            app.run()
            

        Parameters
        -----------
        name: :class:`str`
            The name of the event to dispatch.
        *args: Any
            The args to pass in to the event listeners.
        **kwargs: Any
            The kwargs to pass in to the event listeners.
        """
        loop = self.loop
        if not loop:
            raise RuntimeError('No loop bound to the application')

        log.debug(f'[Application] Dispatching event: {name!r}.')
        name = 'on_' + name

        listeners = self._get_listeners(name)
        if not listeners:
            future = self.loop.create_future()
            future.set_result([])

            return future

        return asyncio.gather(*[self._run_listener(listener, *args, **kwargs) for listener in listeners])

    def add_view(self, view: Union[HTTPView, Type[HTTPView]], *, path: Optional[str] = None) -> HTTPView:
        """
        Adds a view to the application.

        Parameters
        ----------
        view: :class:`~subway.views.HTTPView`
            The view to add. Could be a class or an instance.

        Raises
        ----------
        RegistrationError: If the `view` argument that was passed in is not a proper view or it's already registered.
        """
        if inspect.isclass(view) and issubclass(view, HTTPView):
            view = view()

        if not isinstance(view, HTTPView):
            raise RegistrationError('Expected HTTPView but got {0!r} instead.'.format(view.__class__.__name__)) # type: ignore

        if path is not None:
            view.path = path

        if view.path in self.views:
            raise RegistrationError('View already registered')

        view.init(router=self.router)
        self._views[view.path] = view

        return view

    def remove_view(self, path: str) -> Optional[HTTPView]:
        """
        Removes a view from the application.

        Parameters
        ----------
        path: :class:`str`
            The path of the view to remove.
        """
        view = self._views.pop(path, None)
        if not view:
            return None

        view.init(router=self.router, remove_routes=True)
        return view

    def view(self, path: Optional[str] = None):
        """
        A decorator that adds a view to the application.

        Parameters
        ----------
        path: :class:`str`
            The path of the view to add.

        Example
        ----------
        .. code-block :: python3

            @app.view('/')
            class Index(subway.HTTPView):
                async def get(self, request: subway.Request):
                    return 'Hello, world!'
            
        """
        def decorator(view: Type[HTTPView]):
            return self.add_view(view, path=path)
        return decorator

    def add_resource(self, resource: Resource) -> Resource:
        """
        Adds a resource to the application.

        Parameters
        ----------
        resource: :class:`~subway.resources.Resource`
            The resource to add.

        Raises
        ----------
        RegistrationError: If the `resource` argument that was passed in is not a proper resource.
        """
        if not isinstance(resource, Resource):
            raise RegistrationError('Expected Resource but got {0!r} instead.'.format(resource.__class__.__name__))
    
        if resource.name in self._resources:
            raise RegistrationError('Resource already registered')

        for middleware in resource.middlewares:
            middleware.parent = resource
            self.router.add_middleware(middleware)

        for route in resource.routes:
            route.parent = resource
            self.router.add_route(route)

        for listener in resource.listeners:
            listener.parent = resource
            
            listeners = self._listeners.setdefault(listener.event, [])
            listeners.append(listener)

        self._resources[resource.name] = resource
        return resource

    def remove_resource(self, name: str) -> Optional[Resource]:
        """
        Removes a resource from the application.

        Parameters
        ----------
        name: :class:`str`
            The name of the resource to remove.
        """
        return self._resources.pop(name, None)

    def resource(self, name: Optional[str] = None) -> Callable[[Type[Resource]], Resource]:
        """
        A decorator that adds a resource to the application.
        You should use :method:`~subway.Application.add_resource` instead of this decorator because 

        Parameters
        ----------
        name: :class:`str`
            The name of the resource to add.

        Example
        ----------
        .. code-block :: python3

            @app.resource('users')
            class Users(Resource):
                def __init__(self):
                    self.users = {}

                @subway.route('/users', 'GET')
                async def get_all(self, request: subway.Request):
                    return self.users
            
        """

        def decorator(cls: Type[Resource]):
            resource = cls()
            if name:
                resource.name = name

            return self.add_resource(resource)

        return decorator

    def include(self, blueprint: Blueprint) -> None:
        """
        Includes a blueprint into the application.

        Parameters
        ----------
        blueprint: :class:`~subway.blueprints.Blueprint`
            The blueprint to include.
        """
        if blueprint.name in self._blueprints:
            raise RegistrationError('Blueprint already registered')

        self.add_router(blueprint.router)
        blueprint.listeners.attach(self)

        self._blueprints[blueprint.name] = blueprint

    # getters

    def get_worker(self, id: int) -> Optional[Worker]:
        """
        Returns the worker with the given ID.

        Parameters
        ----------
        id: :class:`int`
            The ID of the worker to return.
        """
        return self._workers.get(id)

    def get_route(self, path: str, method: str) -> Optional[Route]:
        """
        Gets a route from the application.

        Parameters
        ----------
        path: :class:`str`
            The path of the route.
        method: :class:`str`
            The method of the route
        """
        resolved = self.router.resolve_from_path(path, method)
        if resolved:
            return resolved.route

    def get_listeners(self, name: str) -> List[Listener]:
        """
        Gets all listeners of a certain event.

        Parameters
        ----------
        name: :class:`str`
            The name of the event.
        """
        return self._get_listeners(name)

    def get_view(self, path: str) -> Optional[HTTPView]:
        """
        Gets a view from the application.

        Parameters
        ----------
        path: :class:`str`
            The path of the view to get.
        """
        return self._views.get(path)

    def get_resource(self, name: str) -> Optional[Resource]:
        """
        Gets a resource from the application.

        Parameters
        ----------
        name: :class:`str`
            The name of the resource to get.
        """
        return self._resources.get(name)

    def get_blueprint(self, name: str) -> Optional[Blueprint]:
        """
        Gets a blueprint from the application.

        Parameters
        ----------
        name: :class:`str`
            The name of the blueprint to get.
        """
        return self._blueprints.get(name)

    def get_status_code_handler(
        self, code: int
    ) -> Optional[StatusCodeCallback]:
        """
        Gets a status code handler from the application.

        Parameters
        ----------
        code: :class:`int`
            The status code of the handler to get.
        """
        return self._status_code_handlers.get(code)

    # event handlers

    async def on_error(
        self,
        request: Request[Application],
        exc: Exception,
        route: Union[PartialRoute, Route]
    ):
        if self._listeners.get('on_error', []):
            return

        if isinstance(exc, HTTPException):
            await request.send(exc)
        else:
            print(f'Ignoring exception in route {route.path!r}:', file=sys.stderr)
            traceback.print_exception(type(exc), exc, exc.__traceback__, file=sys.stderr)

            await request.send(InternalServerError('An internal server error occurred.'))

    async def on_event_error(self, listener: Listener, exc: Exception):
        if self._listeners.get('on_event_error', []):
            return

        print(f'Ignoring exception in {listener.event!r}:', file=sys.stderr)
        traceback.print_exception(type(exc), exc, exc.__traceback__, file=sys.stderr)
