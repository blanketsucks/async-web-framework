
from .request import Request
from .errors import *
from .server import HTTPProtocol, WebsocketProtocol
from .router import Router
from .response import Response, JSONResponse
from .utils import format_exception, jsonify
from .settings import Settings
from .objects import Route, Listener, Middleware, WebsocketRoute
from .shards import Shard
from .base import AppBase

import json
import inspect
import typing
import yarl
import jwt
import datetime
import asyncpg
import aiosqlite
import aioredis
import asyncio
import pathlib
import importlib
import watchgod

METHODS = ("GET", "POST", "PUT", "HEAD", "OPTIONS", "PATCH", "DELETE")

class HTTPView:
    async def dispatch(self, request, *args, **kwargs):
        coro = getattr(self, request.method.lower(), None)

        if coro:
            await coro(*args, **kwargs)

class Application(AppBase):
    """
    
    ## Listeners order

    `on_startup` -> `on_connection_made` -> `on_request` -> `on_socket_receive` -> `on_connection_lost` -> `on_shutdown`
    
    """
    def __init__(self, routes: typing.List[Route]=None,
                listeners: typing.List[Listener]=None,
                middlewares: typing.List[Middleware]=None, *,
                loop: asyncio.AbstractEventLoop=None,
                url_prefix: str=None,
                settings_file: typing.Union[str, pathlib.Path]=None,
                load_settings_from_env: bool=False) -> None:

        self.loop = loop or asyncio.get_event_loop()
        self.settings = Settings()

        if settings_file:
            self.settings.from_file(settings_file)

        if load_settings_from_env:
            self.settings.from_env_vars()

        self._database_connection = None
        self.router = Router()
        self._server = None
        self._ready = asyncio.Event(loop=self.loop)

        self.url_prefix = url_prefix
        self.shards: typing.Dict[str, Shard] = {}
        self.views = []

        self._is_websocket = False
        super().__init__(routes=routes,
                        listeners=listeners,
                        middlewares=middlewares,
                        url_prefix=url_prefix,
                        loop=self.loop
                        )

    # Private methods

    async def _watch_for_changes(self):
        async for changes in watchgod.awatch('.', watcher_cls=watchgod.PythonWatcher):
            for change in changes:
                self.__datetime = datetime.datetime.utcnow().strftime('%Y-%m-%d | %H:%M:%S')
                print(f"[{self.__datetime}]: Detected change in {change[1]}. Reloading.")

                filepath = change[1][2:-3].replace('\\', '.')
                
                module = importlib.import_module(filepath)
                importlib.reload(module)

                await self.restart()

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

            if len(self._middlewares) != 0:
                await asyncio.gather(*[middleware(request, route.coro) for middleware in self._middlewares])

            args = self._convert(route.coro, args)

            if isinstance(route, Route):
                resp = await route(request, *args)

                if isinstance(resp, dict) or isinstance(resp, list):
                    data = json.dumps(resp)
                    resp = JSONResponse(data)

                if isinstance(resp, str):
                    resp = Response(resp)

            if isinstance(route, WebsocketRoute):
                print('Dispatching websocket...')
                protocol = request.protocol
                print(protocol)
                ws = await protocol._websocket(request, route.subprotocols)
                print(ws)

                task = self.loop.create_task(route(request, ws, *args))

        except HTTPException as exc:
            resp = format_exception(exc)
            raise exc

        except Exception as exc:
            resp = format_exception(exc)
            raise exc

        response_writer(resp)

    # Ready up stuff

    async def wait_until_startup(self):
        await self._ready.wait()

    def is_ready(self):
        return self._ready.is_set()

    # Properties 

    @property
    def routes(self):
        return self.router.routes

    @property
    def shard_count(self):
        return len(self.shards)

    @property
    def running_tasks(self):
        return len([task for task in self._tasks if task.is_running])

    # Some methods. idk

    def get_database_connection(self) -> typing.Optional[typing.Union[asyncpg.pool.Pool, aioredis.Redis, aiosqlite.Connection]]:
        return self._database_connection

    def make_server(self, cls: typing.Union[HTTPProtocol, WebsocketProtocol]=...) -> typing.Union[HTTPProtocol, WebsocketProtocol]:
        cls = WebsocketProtocol if self._is_websocket else HTTPProtocol
            
        res = cls(loop=self.loop, app=self)
        return res

    # Running, closing and restarting the app

    async def start(self, host: typing.Optional[str]=None, *, port: typing.Optional[int]=None, debug: bool=False):
        port = port or self.settings.PORT
        host = host or self.settings.HOST
        debug = debug or self.settings.DEBUG

        serv = self.make_server()
        self._server = server = await self.loop.create_server(lambda: serv, host=host, port=port)

        await self.dispatch("on_startup")
        self._ready.set()
        
        print(f'[{datetime.datetime.utcnow().strftime("%Y-%m-%d | %H:%M:%S")}]: App started. Running at http://{host}:{port}.')
        if debug:
            self.settings.DEBUG = True
            await self._watch_for_changes()

        await server.serve_forever()

    async def close(self):
        if not self._server:
            raise RuntimeError('The app is not running.')

        for task in self._tasks:
            task.stop()

        await self.dispatch('on_shutdown')
        self._server.close()

        await self._server.wait_closed()

    def run(self, *args, **kwargs):
        self._start_tasks()
        try:
            self.loop.run_until_complete(self.start(*args, **kwargs))
        except KeyboardInterrupt:
            self.loop.run_until_complete(self.close())
        finally:
            self.loop.close()

    async def restart(self):
        """
        The main reason i just dont call `close` and then `start` is because of the listeners dispatched inside of them.
        Not having `on_shutdown` and `on_startup` be called on each save would be very nice i believe.
        """
        self._server.close()
        await self._server.wait_closed()

        debug = self.settings.DEBUG

        port = self.settings.PORT
        host = self.settings.HOST

        serv = self.make_server()
        self._server = server = await self.loop.create_server(lambda: serv, host=host, port=port)
        
        await self.dispatch('on_restart')
        print(f'[{datetime.datetime.utcnow().strftime("%Y-%m-%d | %H:%M:%S")}]: App restarted. Running at http://{host}:{port}.')
        if debug:
            await self._watch_for_changes()

        await server.serve_forever()

    # websocket stuff

    def enable_websockets(self):
        self._is_websocket = True

    def disable_websockets(self):
        self._is_websocket = False

    def websocket(self, path: str, method: str, *, subprotocols=None):
        def decorator(coro):
            self.enable_websockets()

            route = WebsocketRoute(path, method, coro)
            route.subprotocols = subprotocols

            return self.add_route(route, websocket=True)
        return decorator

    # Routing

    def add_route(self, route: typing.Union[Route, WebsocketRoute], *, websocket: bool=False):
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

        self.router.add_route(route)
        return route

    def add_protected_route(self, path: typing.Union[str, yarl.URL], method: str, coro: typing.Coroutine):
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
                                    client_secret: str, *,
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

    # dispatching

    async def dispatch(self, name: str, *args, **kwargs):
        try:
            listeners = self._listeners[name]
        except KeyError:
            return
        
        return await asyncio.gather(*[listener(*args, **kwargs) for listener in listeners], loop=self.loop)

    # Shards

    def register_shard(self, shard: Shard):
        shard._inject(self)
        self.shards[shard.name] = shard

        return shard

    # Views

    def register_view(self, view: HTTPView, path: str):
        if not issubclass(view, HTTPView):
            raise ViewRegistrationError('Expected HTTPView but got {0!r} instead.'.format(view.__class__.__name__))

        for method in METHODS:
            if method.lower() in view.__dict__:
                coro = view.__dict__[method.lower()]

                route = Route(path, coro.__name__.upper(), coro)
                self.add_route(route)  

        self.views.append(view)
        return view


    # Getting stuff

    def get_shard(self, name: str):
        try:
            shard = self.shards[name]
        except KeyError:
            return None

        return shard
    