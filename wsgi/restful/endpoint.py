from .meta import EndpointMeta
from ..application import Route
import functools
import typing

if typing.TYPE_CHECKING:
    from ..application import Application
    from .restful import App

class Endpoint(metaclass=EndpointMeta):
    def __init__(self, app: typing.Union['Application', 'App'], path: str) -> None:
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
    def middleware(func):
        func.__endpoint_middleware__ = func
        return func

    def _unpack(self):
        for method, handler in self.__endpoint_routes__.items():
            actual = functools.partial(handler, self)

            route = Route(self.path, method, actual)
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
        