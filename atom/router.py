import inspect
from typing import Callable, Coroutine, List, Dict, Tuple, Union
import re

from .abc import AbstractRouter
from .errors import RegistrationError
from .objects import Route, WebsocketRoute

__all__ = (
    'Router',
)

class Router(AbstractRouter):
    _param_regex = r"{(?P<param>\w+)}"
    def __init__(self) -> None:
        self.routes: Dict[Tuple[str, str], Union[Route, WebsocketRoute]] = {}
        self.middlewares: List[Callable[..., Coroutine]] = []

    def _format_pattern(self, path: str):
        if not re.search(self._param_regex, path):
            return path

        regex = r""
        last_pos = 0

        for match in re.finditer(self._param_regex, path):
            regex += path[last_pos: match.start()]
            param = match.group("param")
            regex += r"(?P<%s>\w+)" % param
            last_pos = match.end()

        return regex

    def add_route(self, route: Union[Route, WebsocketRoute]):
        if isinstance(route, WebsocketRoute):
            self.routes[(route.path, route.method)] = route
            return route

        pattern = self._format_pattern(route.path)
        route.path = pattern

        self.routes[(route.path, route.method)] = route
        return route

    def remove_route(self, route: Union[Route, WebsocketRoute]):
        return self.routes.pop((route.path, route.method), None)

    def websocket(self, path: str):
        def wrapper(func):
            route = WebsocketRoute(path, func, router=self)
            self.add_route(route)

            return route
        return wrapper

    def get(self, path: str):
        def wrapper(func):
            route = Route(path, 'GET', func, router=self)
            self.add_route(route)

            return route
        return wrapper

    def post(self, path: str):
        def wrapper(func):
            route = Route(path, 'POST', func, router=self)
            self.add_route(route)

            return route
        return wrapper

    def put(self, path: str):
        def wrapper(func):
            route = Route(path, 'PUT', func, router=self)
            self.add_route(route)

            return route
        return wrapper

    def delete(self, path: str):
        def wrapper(func):
            route = Route(path, 'DELETE', func, router=self)
            self.add_route(route)

            return route
        return wrapper

    def patch(self, path: str):
        def wrapper(func):
            route = Route(path, 'PATCH', func, router=self)
            self.add_route(route)

            return route
        return wrapper

    def options(self, path: str):
        def wrapper(func):
            route = Route(path, 'OPTIONS', func, router=self)
            self.add_route(route)

            return route
        return wrapper

    def head(self, path: str):
        def wrapper(func):
            route = Route(path, 'HEAD', func, router=self)
            self.add_route(route)

            return route
        return wrapper

    def middleware(self, func):
        if not inspect.iscoroutinefunction(func):
            raise RegistrationError('Middleware callbacks must be coroutine functions')

        self.middlewares.append(func)
        return func

    def __iter__(self):
        return self.routes.values().__iter__()
