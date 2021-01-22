from .meta import ExtensionMeta
from ..application import Route
import functools

class Extension(metaclass=ExtensionMeta):
    def __init__(self, app) -> None:
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
    def middleware(func):
        func.__extension_middleware__ = func
        return func

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
        

    