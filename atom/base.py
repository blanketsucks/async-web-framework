import asyncio

from .objects import Route, Listener, Middleware
from .errors import *
from .tasks import Task

import typing
import yarl
import inspect

class AppBase:
    def __init__(self, routes: typing.List[Route]=None,
                listeners: typing.List[Listener]=None,
                middlewares: typing.List[Middleware]=None, *,
                url_prefix: str=None,
                loop: asyncio.AbstractEventLoop=None) -> None:
        
        self.url_prefix = '' if not url_prefix else url_prefix
        self.loop = loop or asyncio.get_event_loop()

        self._listeners: typing.Dict[str, typing.List[typing.Coroutine]] = {}
        self._middlewares: typing.List[typing.Coroutine] = []
        self._tasks: typing.List[Task] = []


        self._load_from_arguments(routes=routes, listeners=listeners, middlewares=middlewares)

    @property
    def listeners(self):
        return self._listeners

    @property
    def tasks(self):
        return self._tasks

    @property
    def middlewares(self):
        return self._middlewares

    def _load_from_arguments(self, *, routes: typing.List[Route]=None,
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

    def add_route(self, route: Route):
        raise NotImplementedError

    def route(self, path: typing.Union[str, yarl.URL], method: str):
        def decorator(func: typing.Coroutine):
            actual = path

            if isinstance(path, yarl.URL):
                actual = path.raw_path

            route = Route(actual, method, func)
            return self.add_route(route)

        return decorator

    def add_listener(self, f: typing.Coroutine, name: str=None) -> Listener:
        if not inspect.iscoroutinefunction(f):
            raise ListenerRegistrationError('All listeners must be async')
        
        actual = f.__name__.lower() if name is None else name.lower()

        if actual in self._listeners:
            self._listeners[actual].append(f)
        else:
            self._listeners[actual] = [f]
    
        return Listener(f, actual)

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

    def get_listener(self, name: str):
        try:
            listener = self._listeners[name]
        except KeyError:
            return None

        return listener