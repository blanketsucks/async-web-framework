
from .request import Request
from .errors import *
from .server import *
from .router import Router
from .utils import format_exception, jsonify, VALID_METHODS, VALID_LISTENERS
from .settings import Settings
from .objects import Route, Listener, Middleware, WebsocketRoute
from .context import Context, _ContextManager
from .cache import Cache
from .views import HTTPView, WebsocketHTTPView
from .tasks import Task
from .meta import EndpointMeta, ExtensionMeta

import inspect
import typing
import yarl
import jwt
import datetime
import asyncpg
import aiosqlite
import functools
import aioredis
import aiohttp
import asyncio
import pathlib
import importlib
import watchgod

__all__ = (
    'Application',
    'Endpoint',
    'Extension'
)

class _RequestContextManager:
    def __init__(self, session: aiohttp.ClientSession, url: str, method: str, **kwargs) -> None:
        self.__session = session

        self.url = url
        self.method = method
        self.kwargs = kwargs

    async def __aenter__(self):
        method = self.method
        url = self.url
        kwargs = self.kwargs

        async with self.__session.request(method, url, **kwargs) as resp:
            return resp

    async def __aexit__(self, _type, value, tb):
        await self.__session.close()
        return self

class Extension(metaclass=ExtensionMeta):
    def __init__(self, app: 'Application') -> None:
        self.app = app

    @staticmethod
    def route(path: str, method: str):
        def wrapper(func):
            func.__extension_route__ = (method, path)
            return func
        return wrapper

    @staticmethod
    def listener(name: str=None):
        def wrapper(func):
            actual = func.__name__ if name is None else name
            func.__extension_listener__ = actual

            return func
        return wrapper

    @staticmethod
    def middleware():
        def decorator(func):
            func.__extension_middleware__ = func
            return func
        return decorator

    def _unpack(self):
        for event, listener in self.__extension_listeners__.items():
            actual = functools.partial(listener, self)
            self.app.add_listener(actual, event)

        for (method, path), handler in self.__extension_routes__.items():
            actual = functools.partial(handler, self)
            actual_path = self.__extension_route_prefix__ + path

            route = Route(actual_path, method, actual)
            self.app.add_route(route)

        for middleware in self.__extension_middlewares__:
            actual = functools.partial(middleware, self)
            self.app.add_middleware(actual)

        return self

    def _pack(self):
        for event, listener in self.__extension_listeners__.items():
            self.app.remove_listener(event)

        for (method, path), handler in self.__extension_routes__.items():
            self.app.remove_route(path, method)

        for middleware in self.__extension_middlewares__:
            self.app.remove_middleware(middleware)

        return self

class Endpoint(metaclass=EndpointMeta):
    def __init__(self, app: 'Application', path: str) -> None:
        self.app = app
        self.path = path

    @staticmethod
    def route(method: str=None):
        def wrapper(func):
            actual = func.__name__.upper() if method is None else method
            func.__endpoint_route__ = actual

            return func
        return wrapper

    @staticmethod
    def middleware():
        def decorator(func):
            func.__endpoint_middleware__ = func
            return func
        return decorator

    def _unpack(self):
        for method, handler in self.__endpoint_routes__.items():
            actual = functools.partial(handler, self)
            actual_path = self.__endpoint_route_prefix__ + self.path

            route = Route(actual_path, method, actual)
            self.app.add_route(route)

        for middleware in self.__endpoint_middlewares__:
            actual = functools.partial(middleware, self)
            self.app.add_middleware(actual)

        return self

    def _pack(self):
        for method, handler in self.__endpoint_routes__.items():
            self.app.remove_route(self.path, method)

        for middleware in self.__endpoint_middlewares__:
            self.app.remove_middleware(middleware)

        return self

class Application:
    """
    
    ## Listeners order

    `on_startup` -> `on_connection_made` -> `on_request` -> `on_socket_receive` -> `on_connection_lost` -> `on_shutdown`
    
    """
    def __init__(self, routes: typing.List[Route]=None,
                listeners: typing.List[Listener]=None,
                middlewares: typing.List[Middleware]=None, 
                extensions: typing.List[typing.Union[pathlib.Path, str]]=None, 
                endpoints: typing.Dict[str, Endpoint]=None,
                *,
                loop: asyncio.AbstractEventLoop=None,
                url_prefix: str=None,
                settings_file: typing.Union[str, pathlib.Path]=None,
                load_settings_from_env: bool=False,
                routes_cache_maxsize: int=64) -> None:

        self._ready = asyncio.Event()
        self._request = asyncio.Event()

        self.loop = loop or asyncio.get_event_loop()
        self.url_prefix = url_prefix or ''

        self.settings = Settings()
        self.router = Router()
        self.cache = Cache(routes_maxsize=routes_cache_maxsize)

        if settings_file:
            self.settings.from_file(settings_file)

        if load_settings_from_env:
            self.settings.from_env_vars()

        self.views: typing.Dict[str, typing.Union[HTTPView, WebsocketHTTPView]] = {}
        self._websocket_tasks: typing.List[asyncio.Task] = []
        self._listeners: typing.Dict[str, typing.List[typing.Coroutine]] = {}
        self._middlewares: typing.List[typing.Coroutine] = []
        self._tasks: typing.List[Task] = []
        self._endpoints: typing.Dict[str, Endpoint] = {}
        self._extensions: typing.Dict[str, Extension] = {}

        self._is_websocket: bool = False
        self.__session: aiohttp.ClientSession = None
        self._server: asyncio.AbstractServer = None
        self._database_connection = None

        self._load_from_arguments(routes, listeners, middlewares, extensions, endpoints)

    def __repr__(self) -> str:
        # {0.__class__.__name__} because of the subclass: RESTApplication
        return '<{0.__class__.__name__} settings={0.settings} cache={0.cache}>'.format(self)

    # Private methods

    def _load_from_arguments(self, routes=None, listeners=None,
                            middlewares=None, extensions=None, endpoints=None):

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

        if extensions:
            for ext in extensions:
                self.register_extension(ext)

        if endpoints:
            for endpoint in endpoints:
                for path, cls in endpoint:
                    self.register_endpoint(cls, path)

        return self

    async def _watch_for_changes(self):
        async for changes in watchgod.awatch('.', watcher_cls=watchgod.PythonWatcher):
            for change in changes:
                self.__datetime = datetime.datetime.utcnow().strftime('%Y-%m-%d | %H:%M:%S')
                print(f"[{self.__datetime}]: Detected change in {change[1]}. Reloading.")

                filepath = change[1][2:-3].replace('\\', '.')
                
                module = importlib.import_module(filepath)
                importlib.reload(module)

    def _start_tasks(self):
            for task in self._tasks:
                task.start()

    def _convert(self, func, args):
        return_args = []
        params = inspect.signature(func)

        for key, value in params.parameters.items():
            for name, match in args.items():
                if key == name:
                    try:
                        param = value.annotation(match)
                    except ValueError:
                        fut = 'Failed conversion to {0!r} for paramater {1!r}.'.format(value.annotation.__name__, key)
                        raise BadConversion(fut) from None
                    else:
                        return_args.append(param)

        return return_args

    async def _handler(self, request: Request, response_writer):
        resp = None
        try:
            args, route = self.router.resolve(request)
            request.route = route

            self.cache.add_route(route, request)
            if len(self._middlewares) != 0:
                await asyncio.gather(*[middleware(request, route.coro) for middleware in self._middlewares])

            args = self._convert(route.coro, args)
            ctx = Context(app=self, request=request, args=tuple(args))

            if isinstance(route, Route):
                resp = await route(ctx, *args)

            if isinstance(route, WebsocketRoute):
                protocol = request.protocol
                ws = await protocol._websocket(request, route.subprotocols)

                task = self.loop.create_task(route(ctx, ws, *args))
                self._websocket_tasks.append(task)

            if isinstance(resp, Context):
                resp = resp.response

                if resp is None:
                    raise RuntimeError('A route should not return None')

            self.cache.set(context=ctx, response=resp, request=request)  
        except HTTPException as exc:
            resp = format_exception(exc)

        except Exception as exc:
            resp = format_exception(exc)
  
        self._request.set()
        response_writer(resp.as_string())

    # context managers

    def context(self):
        if not self.cache.context:
            raise RuntimeError('a Context object has not been set')
        
        return _ContextManager(self.cache.context)

    # Ready up stuff

    async def wait_until_request(self):
        await self._request.wait()

    async def wait_until_startup(self):
        await self._ready.wait()

    def is_ready(self):
        return self._ready.is_set()

    # Properties

    @property
    def shard_count(self):
        return len(self.shards)

    @property
    def running_tasks(self):
        return len([task for task in self._tasks if task.is_running])

    @property
    def sockets(self) -> typing.Tuple:
        return self._server.sockets if self._server else ()

    @property
    def listeners(self):
        return self._listeners

    @property
    def tasks(self):
        return self._tasks

    @property
    def middlewares(self):
        return self._middlewares

    @property
    def endpoints(self):
        return self._endpoints

    @property
    def extensions(self):
        return self._extensions

    # Some methods. idk

    def get_database_connection(self) -> typing.Optional[typing.Union[asyncpg.pool.Pool, aioredis.Redis, aiosqlite.Connection]]:
        return self._database_connection


    # Running, closing and restarting the app

    async def start(self,
                    host: str=None,
                    port: int=None, 
                    path: str=None,
                    *,
                    debug: bool=False,
                    websocket: bool=False,
                    unix: bool=False,
                    websocket_timeout: float=20,
                    websocket_ping_interval: float=20,
                    websocket_ping_timeout: float=20,
                    websocket_max_size: int=None,
                    websocket_max_queue: int=None,
                    websocket_read_limit: int=2 ** 16,
                    websocket_write_limit: int=2 ** 16,
                    **kwargs):
        
        async def runner():
            return await run_server(self, self.loop, host, port, **kwargs)

        if websocket:
            async def runner():
                return await run_websocket_server(
                    self, self.loop, host, port,
                    timeout=websocket_timeout,
                    ping_interval=websocket_ping_interval,
                    ping_timeout=websocket_ping_timeout,
                    max_size=websocket_max_size,
                    max_queue=websocket_max_queue,
                    read_limit=websocket_read_limit,
                    write_limit=websocket_write_limit, **kwargs
                )

            if unix:
                async def runner():
                    return await run_unix_server(
                        self, self.loop, path, websocket=True,
                        websocket_timeout=websocket_timeout,
                        websocket_ping_interval=websocket_ping_interval,
                        websocket_ping_timeout=websocket_ping_timeout,
                        websocket_max_size=websocket_max_size,
                        websocket_max_queue=websocket_max_queue,
                        websocket_read_limit=websocket_read_limit,
                        websocket_write_limit=websocket_write_limit, **kwargs
                    )

        if unix and not websocket:
            async def runner():
                return await run_unix_server(
                    self, self.loop, path, **kwargs
                )

        async def actual():
            return await runner()

        if debug:
            async def actual():
                await self._watch_for_changes()
                return await runner()

        print(f'[{datetime.datetime.utcnow().strftime("%Y-%m-%d | %H:%M:%S")}] App running.')
        self._ready.set()

        self._start_tasks()
        return await actual()

    async def close(self):
        server = self._server
        if not server:
            raise AppError('The Application is not running')

        server.close()

        await self.dispatch('on_shutdown')
        await server.wait_closed()

    def run(self, *args, **kwargs):
        try:
            self.loop.run_until_complete(self.start(*args, **kwargs))
        except KeyboardInterrupt:
            self.loop.run_until_complete(self.close())
        finally:
            self.loop.close()
            
    # websocket stuff

    def websocket(self, 
                  path: str, 
                  method: str, 
                  *, 
                  subprotocols=None):
        def decorator(coro):
            route = WebsocketRoute(path, method, coro)
            route.subprotocols = subprotocols

            return self.add_route(route, websocket=True)
        return decorator

    # Routing

    def route(self, path: typing.Union[str, yarl.URL], method: str):
        def decorator(func: typing.Coroutine):
            actual = path

            if isinstance(path, yarl.URL):
                actual = path.raw_path

            route = Route(actual, method, func)
            return self.add_route(route)

        return decorator

    def add_route(self,
                  route: typing.Union[Route, WebsocketRoute],
                  *, 
                  websocket: bool=False):
        if not websocket:
            if not isinstance(route, Route):
                raise RouteRegistrationError('Expected Route but got {0!r} instead.'.format(route.__class__.__name__))

        if not inspect.iscoroutinefunction(route.coro):
            raise RouteRegistrationError('Routes must be async.')

        if route in self.router.routes:
            raise RouteRegistrationError('{0!r} is already a route.'.format(route.path))

        if websocket:
            if not isinstance(route, WebsocketRoute):
                fmt = 'Expected WebsocketRoute but got {0!r} instead'
                raise WebsocketRouteRegistrationError(fmt.format(route.__class__.__name__))

            self.router.add_route(route.path, route.method, route.coro, websocket=True)
            return route

        self.router.add_route(route.path, route.method, route.coro)
        return route

    def add_protected_route(self, 
                            path: typing.Union[str, yarl.URL],
                            method: str,
                            coro: typing.Coroutine):
        async def func(request: Request):
            token = request.token
            valid = self.validate_token(token)

            if not valid:
                return jsonify(message='Invalid Token.', status=403)

            return await coro(request)

        if isinstance(path, yarl.URL):
            path = path.raw_path

        route = Route(path, method, func)
        return self.add_route(route)

    def protected(self, path: typing.Union[str, yarl.URL], method: str):
        def decorator(func: typing.Coroutine):
            return self.add_protected_route(path, method, func)
        return decorator

    async def generate_oauth2_token(self,
                                    client_id: str, 
                                    client_secret: str, 
                                    *,
                                    validator: typing.Coroutine=None, 
                                    expires: int=60) -> typing.Optional[bytes]:
        if validator:
            await validator(client_secret)

        try:
            secret_key = self.settings.SECRET_KEY
            data = {
                'user' : client_id,
                'exp' : datetime.datetime.utcnow() + datetime.timedelta(minutes=expires)
            }
        
            token = jwt.encode(data, secret_key)
            return token
        except Exception:
            return None


    def validate_token(self, token: typing.Union[str, bytes]):
        secret = self.settings.SECRET_KEY

        try:
            data = jwt.decode(token, secret)
        except:
            return False

        return True

    def add_oauth2_login_route(self, 
                               path: typing.Union[str, yarl.URL],
                               method: str,
                               coro: typing.Coroutine=None,
                               validator: typing.Coroutine=None,
                               expires: int=60, *,
                               websocket_route: bool=False
                               ) -> typing.Union[Route, WebsocketRoute]:
        if isinstance(path, yarl.URL):
            path = path.raw_path

        if websocket_route:
            async def with_websocket(req: Request, websocket):
                client_id = req.headers.get('client_id')
                client_secret = req.headers.get('client_secret')

                if client_id and client_secret:
                    token = self.generate_oauth2_token(
                        client_id=client_id,
                        client_secret=client_secret,
                        validator=validator, 
                        expires=expires
                    )

                    if coro:
                        return await coro(req, websocket, token)
                    
                    return jsonify(access_token=token)

                if not client_secret or not client_id:
                    return abort(message='Missing client_id or client_secret.', status_code=403)

                route = WebsocketRoute(path, method, with_websocket)
                return self.add_route(route, websocket=True)

        async def without_websocket(request: Request):
            client_id = request.headers.get('client_id')
            client_secret = request.headers.get('client_secret')

            if client_id and client_secret:
                token = self.generate_oauth2_token(client_id, client_secret,
                                                validator=validator, expires=expires)

                if coro:
                    return await coro(request,token)
                
                return jsonify(access_token=token)

            if not client_secret or not client_id:
                return abort(message='Missing client_id or client_secret.', status_code=403)

        route = Route(path, method, without_websocket)
        return self.add_route(route)

    def oauth2(self,
               path: typing.Union[str, yarl.URL],
               method: str,
               validator: typing.Coroutine=None,
               expires: int=60, *,
               websocket_route: bool=False
               )-> typing.Union[Route, WebsocketRoute]:
        def decorator(func):
            return self.add_oauth2_login_route(
                path=path,
                method=method, 
                corr=func,
                validator=validator, 
                expires=expires,
                websocket_route=websocket_route
            )
        return decorator


    def get(self, 
            path: typing.Union[str, yarl.URL], 
            *, 
            websocket: bool=False, 
            websocket_subprotocols=None):
        def decorator(func):
            if websocket:
                return self.websocket(path, 'GET', websocket_subprotocols)(func)

            return self.route(path, 'GET')(func)
        return decorator

    def put(self, 
            path: typing.Union[str, yarl.URL], 
            *, 
            websocket: bool=False, 
            websocket_subprotocols=None):
        def decorator(func):
            if websocket:
                return self.websocket(path, 'PUT', websocket_subprotocols)(func)

            return self.route(path, 'PUT')(func)
        return decorator

    def post(self, 
            path: typing.Union[str, yarl.URL], 
            *, 
            websocket: bool=False, 
            websocket_subprotocols=None):
        def decorator(func):
            if websocket:
                return self.websocket(path, 'POST', websocket_subprotocols)(func)

            return self.route(path, 'POST')(func)
        return decorator

    def delete(self, 
            path: typing.Union[str, yarl.URL], 
            *, 
            websocket: bool=False, 
            websocket_subprotocols=None):
        def decorator(func):
            if websocket:
                return self.websocket(path, 'DELETE', websocket_subprotocols)(func)

            return self.route(path, 'DELETE')(func)
        return decorator

    def head(self, 
            path: typing.Union[str, yarl.URL], 
            *, 
            websocket: bool=False, 
            websocket_subprotocols=None):
        def decorator(func):
            if websocket:
                return self.websocket(path, 'HEAD', websocket_subprotocols)(func)

            return self.route(path, 'HEAD')(func)
        return decorator

    def options(self, 
            path: typing.Union[str, yarl.URL], 
            *, 
            websocket: bool=False, 
            websocket_subprotocols=None):
        def decorator(func):
            if websocket:
                return self.websocket(path, 'OPTIONS', websocket_subprotocols)(func)

            return self.route(path, 'OPTIONS')(func)
        return decorator

    def patch(self, 
            path: typing.Union[str, yarl.URL], 
            *, 
            websocket: bool=False, 
            websocket_subprotocols=None):
        def decorator(func):
            if websocket:
                return self.websocket(path, 'PATCH', websocket_subprotocols)(func)

            return self.route(path, 'PATCH')(func)
        return decorator

    # dispatching and listeners

    def add_listener(self, coro: typing.Coroutine, name: str=None):
        if not inspect.iscoroutinefunction(coro):
            raise ListenerRegistrationError('Listeners must be coroutines')

        actual = name if name else coro.__name__

        if not actual in VALID_LISTENERS:
            raise ListenerRegistrationError(f'{actual!r} is not a valid listener')

        if actual in self._listeners.keys():
            self._listeners[actual].append(coro)
            return Listener(coro, actual)

        self._listeners[actual] = [coro]
        return Listener(coro, actual)

    def remove_listener(self, func: typing.Coroutine=None, name: str=None):
        if not func:
            if name:
                coros = self._listeners.pop(name.lower())
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
            if isinstance(listener, asyncio.Future):
                if len(args) == 0:
                    listener.set_result(None)
                elif len(args) == 1:
                    listener.set_result(args[0])
                else:
                    listener.set_result(args)

                listeners.remove(listener)
    
        return await asyncio.gather(*[listener(*args, **kwargs) for listener in listeners], loop=self.loop)

    # Shards

    # Views

    def register_view(self, view: HTTPView, path: str):
        if not issubclass(view, HTTPView):
            raise ViewRegistrationError('Expected HTTPView but got {0!r} instead.'.format(view.__class__.__name__))

        for method in VALID_METHODS:
            if method.lower() in view.__dict__:
                coro = view.__dict__[method.lower()]

                route = Route(path, coro.__name__.upper(), coro)
                self.add_route(route)  

        self.views[path] = view
        return view

    def register_websocket_view(self, view: WebsocketHTTPView, path: str):
        if not issubclass(view, WebsocketHTTPView):
            raise ViewRegistrationError('Expected WebsocketHTTPView but got {0!r} instead.'.format(view.__class__.__name__))

        for method in VALID_METHODS:
            if method.lower() in view.__dict__:
                coro = view.__dict__[method.lower()]

                route = WebsocketRoute(path, coro.__name__.upper(), coro)
                self.add_route(route, websocket=True)  

        self.views[path] = view
        return view

    # middlewares

    def middleware(self):
        def wrapper(func: typing.Coroutine):
            return self.add_middleware(func)
        return wrapper

    def add_middleware(self, middleware: typing.Coroutine):
        if not inspect.iscoroutinefunction(middleware):
            raise MiddlewareRegistrationError('All middlewares must be async')

        self._middlewares.append(middleware)
        return Middleware(middleware)

    def remove_middleware(self, middleware: typing.Coroutine) -> typing.Coroutine:
        self._middlewares.remove(middleware)
        return middleware

    # extensions

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

    # endpoints

    def register_endpoint(self, cls, path: str):
        if not issubclass(cls, Endpoint):
            raise EndpointLoadError('Expected Endpoint but got {0!r} instead.'.format(cls.__name__))
        
        res = cls(self, path)
        res._unpack()

        self._endpoints[res.__endpoint_name__] = res
        return res

    def remove_endpoint(self, name: str):
        if not name in self._endpoints:
            raise EndpointNotFound('{0!r} was not found.'.format(name))

        endpoint = self._endpoints.pop(name)
        endpoint._pack()

        return endpoint

    def endpoint(self, path: str):
        def decorator(cls):
            return self.register_endpoint(cls, path)
        return decorator

    # tasks

    def add_task(self, coro, *, seconds: int=0, minutes: int=0, hours: int=0, count: int=0):
        kwargs = {
            'coro': coro,
            'seconds': seconds,
            'minutes': minutes,
            'hours': hours,
            'count': count,
            'loop': self.loop
        }

        task = Task(**kwargs)
        self._tasks.append(task)

        return task

    def task(self, *, seconds: int=0, minutes: int=0, hours: int=0, count: int=0):
        def decorator(coro):
            return self.add_task(coro, seconds=seconds, minutes=minutes, hours=hours, count=count)
        return decorator

    # Getting stuff

    def get_routes(self) -> typing.Iterator[typing.Union[Route, WebsocketRoute]]:
        yield from self.router.routes

    def get_listeners(self, name: str) -> typing.Iterator[typing.Coroutine]:
        yield from self._listeners[name]

    
    # test client

    def request(self, route: str, method: str, **kwargs):
        if not self.__session or self.__session.closed:
            self.__session = aiohttp.ClientSession(loop=self.loop)

        url = self.settings.HOST + route
        session = self.__session

        return _RequestContextManager(session, url, method, **kwargs)

    # waiting for stuff

    async def wait_for(self, event: str, *, timeout: int=120.0):
        future = self.loop.create_future()
        listeners = self._listeners.get(event.lower())

        print(future)
        if not listeners:
            listeners = []
            self._listeners[event.lower()] = listeners

        listeners.append(future)
        return await asyncio.wait_for(future, timeout=timeout)