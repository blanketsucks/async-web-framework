from atom.meta import ExtensionMeta
from atom.objects import Listener, Middleware, Route

import typing
import functools

if typing.TYPE_CHECKING:
    from atom.app import Application

class Extension(metaclass=ExtensionMeta):
    def __init__(self, app: 'Application') -> None:
        self.app = app

    def _unpack(self):
        for listener in self.__extension_listeners__:
            actual = functools.partial(listener.coro, self)
            self.app.add_listener(actual, listener.event)

        for route in self.__extension_routes__:
            actual = functools.partial(route.coro, self)
            actual_path = self.__extension_route_prefix__ + route.path

            actual_route = Route(actual_path, route.method, actual)
            self.app.add_route(actual_route)

        for middleware in self.__extension_middlewares__:
            actual = functools.partial(middleware.coro, self)
            self.app.add_middleware(actual)

        return self

    def _pack(self):
        for listener in self.__extension_listeners__:
            self.app.remove_listener(listener.event)

        for route in self.__extension_routes__:
            self.app.remove_route(route)

        for middleware in self.__extension_middlewares__:
            self.app.remove_middleware(middleware.coro)

        return self

    @staticmethod
    def route(path: str, method: str=...):
        def decorator(func: typing.Callable):
            actual = 'GET' if method is ... else method
            route = Route(path, actual, func)

            func.__route__ = route
            return func
        return decorator

    @staticmethod
    def listener(name: str=...):
        def decorator(func: typing.Callable):
            actual = func.__name__ if name is ... else name
            listener = Listener(func, actual)

            func.__listener__ = listener
            return func
        return decorator

    @staticmethod
    def middleware(func: typing.Callable):
        middleware = Middleware(func)

        func.__middleware__ = middleware
        return func