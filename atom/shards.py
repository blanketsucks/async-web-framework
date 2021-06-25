import typing
import asyncio

from atom.objects import Route, Listener, WebsocketRoute
from atom.errors import RouteRegistrationError, ListenerRegistrationError
from .datastructures import URL
from .typings import Awaitable
from .views import HTTPView, WebsocketHTTPView
from .errors import ViewRegistrationError

if typing.TYPE_CHECKING:
    from atom.app import Application


class Shard:
    def __init__(self, name: str, url_prefix: str = '', *, loop: asyncio.AbstractEventLoop = None):
        self.name = name
        self.url_prefix = url_prefix

        self.routes: typing.List[Route] = []
        self.views: typing.List[typing.Union[WebsocketHTTPView, HTTPView]] = []
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

        return app.shards.pop(self.name)

    def _unpack(self, app: 'Application'):
        for route in self.routes:
            app.add_route(route)

        for view in self.views:
            app.register_view(view)

        for name, listener in self.listeners.items():
            listeners = app.listeners.setdefault(name, [])
            listeners.append(listener)

        return self

    def add_route(self, route: Route):
        if not isinstance(route, (Route, WebsocketRoute)):
            raise RouteRegistrationError('Expected Route but got {0.__class__.__name__} instead'.format(route))

        self.routes.append(route)
        return route

    def remove_route(self, route: typing.Union[Route, WebsocketRoute]):
        self.routes.remove(route)
        return route

    def route(self, path: str, method: str):
        def decorator(func) -> Route:
            if not asyncio.iscoroutinefunction(func):
                raise ValueError('Routes must be async')

            route = Route(path, method, func, app=self)
            return self.add_route(route)
        return decorator

    def websocket(self, path: str):
        def decorator(coro: Awaitable) -> WebsocketRoute:
            if not asyncio.iscoroutinefunction(coro):
                raise ValueError('Routes must be async')

            route = WebsocketRoute(path, 'GET', coro, app=self)
            return self.add_route(route)
        return decorator

    def get(self, path: typing.Union[str, URL]):
        def decorator(func: Awaitable) -> Route:
            return self.route(path, 'GET')(func)
        return decorator

    def put(self, path: typing.Union[str, URL]):
        def decorator(func: Awaitable):
            return self.route(path, 'PUT')(func)
        return decorator

    def post(self, path: typing.Union[str, URL]):
        def decorator(func: Awaitable):
            return self.route(path, 'POST')(func)
        return decorator

    def delete(self, path: typing.Union[str, URL]):
        def decorator(func: Awaitable):
            return self.route(path, 'DELETE')(func)
        return decorator

    def head(self, path: typing.Union[str, URL]):
        def decorator(func: Awaitable):
            return self.route(path, 'HEAD')(func)
        return decorator

    def options(self, path: typing.Union[str, URL]):
        def decorator(func: Awaitable):
            return self.route(path, 'OPTIONS')(func)
        return decorator

    def patch(self, path: typing.Union[str, URL]):
        def decorator(func: Awaitable):
            return self.route(path, 'PATCH')(func)
        return decorator

    def listener(self, name: str = None):
        def decorator(func):
            actual = func.__name__ if not name else name

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

    def middleware(self, route: Route):
        def wrapper(func: Awaitable):
            return route.add_middleware(func)
        return wrapper

    def register_view(self, view: typing.Union[HTTPView, WebsocketHTTPView]):
        if not isinstance(view, (HTTPView, WebsocketHTTPView)):
            raise ViewRegistrationError('Expected HTTPView but got {0!r} instead.'.format(view.__class__.__name__))

        self.views.append(view)
        return view

    def view(self, path: str):
        def decorator(cls):
            if cls.__url_route__ == '':
                cls.__url_route__ = path

            view = cls()
            return self.register_view(view)
        return decorator
