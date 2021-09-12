"""
MIT License

Copyright (c) 2021 blanketsucks

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
import inspect
from typing import Callable, List, Dict, Optional, Tuple, Union
import re

from ._types import CoroFunc

from .errors import RegistrationError
from .objects import Middleware, Route, WebsocketRoute


__all__ = (
    'Router',
)

class Router:
    """
    A route handler.

    Parameters
    ----------
    url_prefix: :class:`str`
        The prefix used for route urls.

    Attributes
    ----------
    url_prefix: 
        The prefix used for route urls.
    routes: 
        A dictionary of routes.
    middlewares: 
        A list of middleware callbacks.
    """
    _param_regex = r"{(?P<param>\w+)}"
    def __init__(self, url_prefix: str) -> None:
        """
        Router constructor.

        Parameters:
            url_prefix: The prefix used for route urls.
        """
        self.url_prefix = url_prefix
        self.routes: Dict[Tuple[str, str], Union[Route, WebsocketRoute]] = {}
        self.middlewares: List[Middleware] = []

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

    def add_route(self, route: Union[Route, WebsocketRoute]) -> Union[Route, WebsocketRoute]:
        """
        Adds a route to the router.

        Parameters
        ----------
        route: :class:`~railway.objects.Route` 
            The route to add.
        """
        path = self.url_prefix + route.path

        if isinstance(route, WebsocketRoute):
            self.routes[(path, route.method)] = route
            return route

        pattern = self._format_pattern(path)
        route.path = pattern

        self.routes[(route.path, route.method)] = route
        return route

    def remove_route(self, route: Union[Route, WebsocketRoute]) -> Optional[Union[Route, WebsocketRoute]]:
        """
        Removes a route from the router.

        Parameters
        ----------
        route: :class:`~railway.objects.Route`
            The route to remove.
        """
        return self.routes.pop((route.path, route.method), None)

    def websocket(self, path: str) -> Callable[[CoroFunc], Route]:
        """
        A decorator for registering a websocket route.

        Parameters
        ----------
        path: :class:`str`
            The path to register the route to.
        """
        def wrapper(func: CoroFunc):
            route = WebsocketRoute(path, 'GET', func, router=self)
            self.add_route(route)

            return route
        return wrapper

    def route(self, path: str, method: str) -> Callable[[CoroFunc], Route]:
        """
        A decorator for registering a route.

        Parameters
        ----------
        path: :class:`str`
            The path to register the route to.
        method: :class:`str`
            The HTTP method to use for the route.
        """
        def wrapper(func: CoroFunc):
            route = Route(path, method, func, router=self)
            self.add_route(route)

            return route
        return wrapper

    def get(self, path: str) -> Callable[[CoroFunc], Route]:
        """
        Adds a :class:`~railway.objects.Route` with the ``GET`` HTTP method.

        Parameters
        ----------
        path: :class:`str`
            The path to the route.
        """
        def decorator(func: CoroFunc) -> Route:
            route = Route(path, 'GET', func, router=self)
            return self.add_route(route)
        return decorator

    def put(self, path: str) -> Callable[[CoroFunc], Route]:
        """
        Adds a :class:`~railway.objects.Route` with the ``PUT`` HTTP method.

        Parameters
        ----------
        path: :class:`str`
            The path to the route.
        """
        def decorator(func: CoroFunc):
            route = Route(path, 'PUT', func, router=self)
            return self.add_route(route)
        return decorator

    def post(self, path: str) -> Callable[[CoroFunc], Route]:
        """
        Adds a :class:`~railway.objects.Route` with the ``POST`` HTTP method.

        Parameters
        ----------
        path: :class:`str`
            The path to the route.
        """
        def decorator(func: CoroFunc):
            route = Route(path, 'POST', func, router=self)
            return self.add_route(route)
        return decorator

    def delete(self, path: str) -> Callable[[CoroFunc], Route]:
        """
        Adds a :class:`~railway.objects.Route` with the ``DELETE`` HTTP method.

        Parameters
        ----------
        path: :class:`str`
            The path to the route.
        """
        def decorator(func: CoroFunc):
            route = Route(path, 'DELETE', func, router=self)
            return self.add_route(route)
        return decorator

    def head(self, path: str) -> Callable[[CoroFunc], Route]:
        """
        Adds a :class:`~railway.objects.Route` with the ``HEAD`` HTTP method.

        Parameters
        ----------
        path: :class:`str`
            The path to the route.
        """
        def decorator(func: CoroFunc):
            route = Route(path, 'HEAD', func, router=self)
            return self.add_route(route)
        return decorator

    def options(self, path: str) -> Callable[[CoroFunc], Route]:
        """
        Adds a :class:`~railway.objects.Route` with the ``OPTIONS`` HTTP method.

        Parameters
        ----------
        path: :class:`str`
            The path to the route.
        """
        def decorator(func: CoroFunc):
            route = Route(path, 'OPTIONS', func, router=self)
            return self.add_route(route)
        return decorator

    def patch(self, path: str) -> Callable[[CoroFunc], Route]:
        """
        Adds a :class:`~railway.objects.Route` with the ``PATCH`` HTTP method.

        Parameters
        ----------
        path: :class:`str`
            The path to the route.
        """
        def decorator(func: CoroFunc):
            route = Route(path, 'PATCH', func, router=self)
            return self.add_route(route)
        return decorator

    def middleware(self, func: CoroFunc) -> Middleware:
        """
        A decorator for registering a middleware callback.

        Parameters
        ----------
        func: Callable[..., Coroutine[Any, Any, Any]]
            The middleware callback.

        """
        if not inspect.iscoroutinefunction(func):
            raise RegistrationError('Middleware callbacks must be coroutine functions')

        middleware = Middleware(func)
        middleware._is_global = True

        self.middlewares.append(middleware)
        return middleware

    def __iter__(self):
        return self.routes.values().__iter__()
