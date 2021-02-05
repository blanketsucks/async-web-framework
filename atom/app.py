
from .request import Request
from .errors import *
from .server import Server
from .router import Router
from .response import Response, JSONResponse
from .utils import format_exception, jsonify
from .settings import Settings
from .objects import Route, Listener, Middleware
from .shards import Shard
from .base import AppBase

import json
import functools
import inspect
import typing
import yarl
import jwt
import datetime
import asyncpg
import aiosqlite
import aioredis
import asyncio
import importlib
import watchgod

class Application(AppBase):
    """
    
    ## Listeners order

    `on_startup` -> `on_connection_made` -> `on_request` -> `on_socket_receive` -> `on_connection_lost` -> `on_shutdown`
    
    """
    def __init__(self, routes: typing.List[Route]=None,
                listeners: typing.List[Listener]=None,
                middlewares: typing.List[Middleware]=None, *,
                loop: asyncio.AbstractEventLoop=None) -> None:

        self.loop = loop or asyncio.get_event_loop()
        self.settings = Settings()

        self._database_connection = None
        self._router = Router()

        self._server = None
        self._running_host = '127.0.0.1'

        self._running_port = 8080
        self._ready = asyncio.Event(loop=self.loop)

        self._shards: typing.Dict[str, Shard] = {}
        super().__init__(routes, listeners, middlewares)

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

    def _load_from_arguments(self, routes: typing.List[Route]=None,
                            listeners: typing.List[Listener]=None,
                            middlewares: typing.List[Middleware]=None):

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
        handler = None
        resp = None

        try:
            args, handler = self._router.resolve(request)

            if len(self._middlewares) != 0:
                for middleware in self._middlewares:
                    handler = functools.partial(middleware, handler)
            
            args = self._convert(handler, args)
            resp = await handler(request, *args)

            if isinstance(resp, dict) or isinstance(resp, list):
                data = json.dumps(resp)
                resp = JSONResponse(data)

            if isinstance(resp, str):
                resp = Response(resp)

        except HTTPException as exc:
            await self.dispatch('on_error', exc)
            resp = format_exception(exc)

        except Exception as exc:
            await self.dispatch('on_error', exc)
            resp = format_exception(exc)

        response_writer(resp)


    # Ready up stuff

    async def wait_until_startup(self):
        await self._ready.wait()

    def is_ready(self):
        return self._ready.is_set()

    # Properties 

    @property
    def router(self):
        return self._router

    @property
    def routes(self):
        return self._router.routes

    @property
    def shards(self):
        return self._shards

    @property
    def shard_count(self):
        return len(self._shards)

    @property
    def running_tasks(self):
        return len([task for task in self._tasks if task.is_running])

    # Some methods. idk

    def get_database_connection(self) -> typing.Optional[typing.Union[asyncpg.pool.Pool, aioredis.Redis, aiosqlite.Connection]]:
        return self._database_connection

    def make_server(self, cls=Server):
        res = cls(self.loop, app=self, handler=self._handler)
        return res
        
    def get_setting(self, key: str):
        value = self.settings.get(key, None)
        return value

    def remove_setting(self, key: str):
        value = self.settings.pop(key)
        return value
    
    def set_setting(self, key, value):
        self.settings[key] = value
        return key, value

    # Running, closing and restarting the app

    async def start(self, host: typing.Optional[str]=None, *, port: typing.Optional[int]=None, debug: bool=False):
        if not host:
            host = '127.0.0.1'

        if not port:
            port = 8080

        self._running_port = port
        self._running_host = host

        serv = self.make_server()
        self._server = server = await self.loop.create_server(lambda: serv, host=host, port=port)

        await self.dispatch("on_startup")
        self._ready.set()
        print(self._ready.is_set())

        print(f'[{datetime.datetime.utcnow().strftime("%Y-%m-%d | %H:%M:%S")}]: App started. Running at http://{host}:{port}.')
        if debug:
            self.settings['DEBUG'] = True
            await self._watch_for_changes()

        await server.serve_forever()

    async def close(self):
        if not self._server:
            raise RuntimeError('The app is not running.')

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

        debug = self.get_setting('DEBUG')

        port = self._running_port
        host = self._running_host

        serv = self.make_server()
        self._server = server = await self.loop.create_server(lambda: serv, host=host, port=port)
        
        await self.dispatch('on_restart')
        print(f'[{datetime.datetime.utcnow().strftime("%Y-%m-%d | %H:%M:%S")}]: App restarted. Running at http://{host}:{port}.')
        if debug:
            await self._watch_for_changes()

        await server.serve_forever()


    # Routing

    def add_route(self, route: Route):
        if not inspect.iscoroutinefunction(route.coro):
            raise RouteRegistrationError('Routes must be async.')

        if (route.method, route.path) in self._router.routes:
            raise RouteRegistrationError('{0!r} is already a route.'.format(route.path))

        self._router.add_route(route)
        return route

    def remove_route(self, path: str, method: str):
        return self._router.remove_route(method, path)

    def get(self, path: typing.Union[str, yarl.URL]):
        def decorator(func: typing.Coroutine):
            return self.route(path, 'GET')(func)
        return decorator

    def put(self, path: typing.Union[str, yarl.URL]):
        def decorator(func: typing.Coroutine):
            return self.route(path, 'PUT')(func)
        return decorator

    def post(self, path: typing.Union[str, yarl.URL]):
        def decorator(func: typing.Coroutine):
            return self.route(path, 'POST')(func)
        return decorator

    def delete(self, path: typing.Union[str, yarl.URL]):
        def decorator(func: typing.Coroutine):
            return self.route(path, 'DELETE')(func)
        return decorator

    def add_protected_route(self, path: typing.Union[str, yarl.URL], method: str, coro: typing.Coroutine):
        async def func(request: Request):
            _type, token = self.get_oauth_token(request.headers)
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

    def generate_oauth2_token(self, client_id: str, client_secret: str, *, validator: typing.Coroutine=None, expires: int=60):
        if validator:
            self.loop.run_until_complete(validator(client_secret))

        secret_key = self.get_setting('SECRET_KEY')
        data = {
            'user' : client_id,
            'exp' : datetime.datetime.utcnow() + datetime.timedelta(minutes=expires)
        }
    
        token = jwt.encode(data, secret_key)
        return token

    def get_oauth_token(self, headers: typing.Dict[str, str]):
        auth = headers.get('Authorization')

        if not auth:
            return None

        _type, token = auth.split(' ')
        return _type, token

    def validate_token(self, token: typing.Union[str, bytes]):
        secret = self.get_setting('SECRET_KEY')

        try:
            data = jwt.decode(token, secret)
        except:
            return False

        return True

    def add_oauth2_login_route(self, path: typing.Union[str, yarl.URL], method: str,
                            coro: typing.Coroutine=None, validator: typing.Coroutine=None, expires: int=60):

        async def func(req: Request):
            client_id = req.headers.get('client_id')
            client_secret = req.headers.get('client_secret')

            if client_id and client_secret:
                token = self.generate_oauth2_token(client_id, client_secret,
                                                validator=validator, expires=expires)

                if coro:
                    return await coro(req, token)
                
                return jsonify(access_token=token)

            if not client_secret or not client_id:
                return jsonify(message='Missing client_id or client_secret.', status=403)

        if isinstance(path, yarl.URL):
            path = path.raw_path

        route = Route(path, method, func)
        return self.add_route(route)

    def oauth2(self, path: typing.Union[str, yarl.URL], method: str,
            validator: typing.Coroutine=None, expires: int=60):
        def decorator(func):
            return self.add_oauth2_login_route(path, method, func, validator=validator, expires=expires)
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
        self._shards[shard.name] = shard

        return shard
    # Getting stuff

    def get_route(self, path: str, method: str):
        try:
            handler = self._router.routes[(path, method)]
        except KeyError:
            return None

        route = Route(path, method, handler)
        return route

    def get_shard(self, name: str):
        try:
            shard = self._shards[name]
        except KeyError:
            return None

        return shard

    # Editing any of the following methods will do nothing since they're here as a refrence for listeners.
    # Unless you manually add them inside a subclass.

    async def on_startup(self): ...

    async def on_shutdown(self): ...

    async def on_error(self, exc: typing.Union[HTTPException, Exception]): ...

    async def on_request(self, request: Request): ...

    async def on_socket_receive(self, data: bytes): ...

    async def on_connection_made(self, transport: asyncio.BaseTransport): ...

    async def on_connection_lost(self, exc: typing.Optional[Exception]): ...

    async def on_database_connect(self, connection: typing.Union[asyncpg.pool.Pool, aioredis.Redis, aiosqlite.Connection]): ...

    async def on_database_close(self): ...

    