import typing
import asyncio

from atom.objects import Route, Listener
from atom.utils import VALID_LISTENERS
from atom.errors import RouteRegistrationError, ListenerRegistrationError

if typing.TYPE_CHECKING:
    from atom.app import Application


class Shard:
    def __init__(self, name: str, url_prefix: str = '', *, loop: asyncio.AbstractEventLoop = None):
        self.name = name
        self.url_prefix = url_prefix

        self.routes: typing.List[Route] = []
        self.listeners: typing.Dict[str, typing.List[typing.Union[asyncio.Future, typing.Callable]]] = {}

        if not loop:
            self.loop = asyncio.get_event_loop()
        else:
            self.loop = loop

    def destroy(self, app: 'Application'):
        for route in self.routes:
            app.remove_route(route)

        for name in self.listeners.keys():
            app.remove_listener(name=name)

        return app.shards.pop(self)

    def _unpack(self, app: 'Application'):
        for route in self.routes:
            app.add_route(route)

        for name, listener in self.listeners.items():
            listeners = app.listeners.setdefault(name, [])
            listeners.append(listener)

        return self

    def add_route(self, route: Route):
        if not isinstance(route, Route):
            raise RouteRegistrationError('Expected Route but got {0.__class__.__name__} instead'.format(route))

        self.routes.append(route)
        return route

    def route(self, path: str, method: str):
        def decorator(func):
            if not asyncio.iscoroutinefunction(func):
                raise ValueError('Routes must be async')

            route = Route(path, method, func)
            return self.add_route(route)

        return decorator

    def listener(self, name: str = None):
        def decorator(func):
            actual = func.__name__ if not name else name

            if actual not in VALID_LISTENERS:
                raise ListenerRegistrationError(f'{actual} is not a valid listener')

            if not asyncio.iscoroutinefunction(func):
                raise ValueError('Listeners must be async')

            listeners = self.listeners.get(actual)
            if not listeners:
                self.listeners[name.lower()] = [func]
            else:
                listeners.append(func)

            listener = Listener(func, name)
            return listener

        return decorator