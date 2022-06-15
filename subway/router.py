from __future__ import annotations

from typing import TYPE_CHECKING, Callable, List, Dict, NamedTuple, Optional, Tuple, Union, TypeVar, Any, NoReturn
from functools import lru_cache
import re
import copy

from .types import CoroFunc, RequestMiddleware, ResponseMiddleware
from .utils import iscoroutinefunction, isasyncgenfunction
from .errors import RegistrationError
from .responses import NotFound, MethodNotAllowed
from .objects import Middleware, Route, WebSocketRoute, MiddlewareType

if TYPE_CHECKING:
    from typing_extensions import ParamSpec

    RouteT = TypeVar('RouteT', bound=Route)

    T = TypeVar('T')
    P = ParamSpec('P')
    
    def lru_cache(maxsize: Optional[int] = 128) -> Callable[[Callable[P, T]], Callable[P, T]]:
        ...

__all__ = (
    'Router',
)

ROUTE_CACHE_MAXSIZE = 2048

class ResolvedRoute(NamedTuple):
    route: Route
    params: Dict[str, str]

    @classmethod
    def from_route(cls, route: Route):
        return cls(route=route, params={})

    @property
    def method(self) -> str:
        return self.route.method

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
    PARAM_REGEX = re.compile(r"{(?P<parameter>\w+)}")

    def __init__(self, url_prefix: Optional[str] = None) -> None:
        """
        Router constructor.

        Parameters:
            url_prefix: The prefix used for route urls.
        """
        self.url_prefix = url_prefix or ''
        self.routes: Dict[Tuple[str, str], Union[Route, WebSocketRoute]] = {}
        self.request_middlewares: List[Middleware] = []
        self.response_middlewares: List[Middleware] = []

    def union(self, other: Router) -> Router:
        """
        Merges two routers.

        Parameters
        ----------
        other: :class:`~subway.Router`
            The router to merge with.
        """
        [self.add_route(route) for route in other]

        self.request_middlewares.extend(other.request_middlewares)
        self.response_middlewares.extend(other.response_middlewares)

        return self

    def clear(self) -> None:
        """
        Clears the router.
        """
        self.routes.clear()
        self.response_middlewares.clear()
        self.request_middlewares.clear()

    @lru_cache(maxsize=ROUTE_CACHE_MAXSIZE)
    def match(self, path: str) -> Optional[ResolvedRoute]:
        """
        Matches a path to a route. Can be slow.

        Parameters
        ----------
        path: :class:`str`
            The path to match.

        Returns
        -------
        :class:`~.ResolvedRoute`
            The resolved route.
        """
        for route in self:
            params = route.match(path)
            if params is not None:
                return ResolvedRoute(route, params)

    @lru_cache(maxsize=ROUTE_CACHE_MAXSIZE)
    def resolve(self, path: str, method: str) -> Optional[ResolvedRoute]:
        """
        Resolves a route.

        Parameters
        ----------
        path: :class:`str`
            The path to resolve the route from.
        method: :class:`str`
            The method to resolve the route from.

        Returns
        -------
        :class:`~.ResolvedRoute`
            The resolved route.
        """
        if path.endswith('/') and not path == '/':
            return self.resolve(path[:-1], method)

        resolved = self.resolve_from_path(path, method)
        if resolved is not None:
            return resolved

        resolved = self.match(path)
        if not resolved:
            raise NotFound(f'Route {path!r} was not found.')

        if resolved.method != method:
            raise MethodNotAllowed(f'Method {method!r} is not allowed for route {path!r}.')

        return resolved

    def resolve_from_path(self, path: Union[Route, str], method: str) -> Optional[ResolvedRoute]:
        """
        Resolves a route from a path.

        Parameters
        ----------
        path: :class:`str`
            The path to resolve the route from.
        method: :class:`str`
            The method to resolve the route from.
        """
        if isinstance(path, Route):
            path = path.raw_path

        route = self.routes.get((path, method))
        if route:
            return ResolvedRoute.from_route(route)

    def format_path_pattern(self, path: str):
        """
        Formats a path pattern.

        Parameters
        ----------
        path: :class:`str`
            The path pattern to format.
        """
        if not self.PARAM_REGEX.search(path):
            return path

        regex = r""
        position = 0

        for match in self.PARAM_REGEX.finditer(path):
            regex += path[position:match.start()] + r"(?P<%s>.+)" % match.group("parameter")
            position = match.end()

        return regex

    def store_route(self, route: RouteT) -> RouteT:
        """
        Stores a route in the router.

        Parameters
        ----------
        route: :class:`~subway.objects.Route`
            The route to store.
        """
        self.routes[(route.raw_path, route.method)] = route
        return route

    def add_route(self, route: RouteT) -> RouteT:
        """
        Adds a route to the router.

        Parameters
        ----------
        route: :class:`~subway.objects.Route` 
            The route to add.
        """
        assert route.raw_path is not None

        if not isinstance(route, (Route, WebSocketRoute)):
            fmt = 'Expected Route or WebSocketRoute but got {0!r} instead'
            raise RegistrationError(fmt.format(route.__class__.__name__))
        
        if not iscoroutinefunction(route.callback) and not isasyncgenfunction(route.callback):
            raise RegistrationError('Route callbacks must be coroutine functions or async generators')

        if route in self:
            raise RegistrationError('{0!r} is already a route.'.format(route.path))

        if isinstance(route, WebSocketRoute):
            return self.store_route(route)

        route.path = self.format_path_pattern(route.path)
        return self.store_route(route)

    def remove_route(self, route: RouteT) -> Optional[RouteT]:
        """
        Removes a route from the router.

        Parameters
        ----------
        route: :class:`~subway.objects.Route`
            The route to remove.
        """
        return self.routes.pop((route.raw_path, route.method), None)  # type: ignore

    def websocket(
        self, 
        path: str, 
        *, 
        name: Optional[str] = None
    ) -> Callable[[Union[CoroFunc, WebSocketRoute]], WebSocketRoute]:
        """
        A decorator for registering a websocket route.

        Parameters
        ----------
        path: :class:`str`
            The path to register the route to.
        name: Optional[:class:`str`]
            The name of the route.
        """
        def decorator(func: Union[CoroFunc, WebSocketRoute]) -> WebSocketRoute:
            route = self.create_websocket_route(func, path, name=name)
            return self.add_route(route) 
        return decorator

    def route(
        self, 
        path: str, 
        method: str, 
        *, 
        name: Optional[str] = None
    ) -> Callable[[Union[CoroFunc, Route]], Route]:
        """
        A decorator for registering a route.

        Parameters
        ----------
        path: :class:`str`
            The path to register the route to.
        method: :class:`str`
            The HTTP method to use for the route.
        name: Optional[:class:`str`]
            The name of the route.
        """
        def decorator(func: Union[CoroFunc, Route]):
            route = self.create_route(func, path, method, name=name)
            return self.add_route(route)
        return decorator

    def _add_middleware(self, type: MiddlewareType, callback: Any) -> Middleware:
        if not iscoroutinefunction(callback):
            raise RegistrationError('Middleware callbacks must be coroutine functions')

        middleware = Middleware(type, callback, router=self) # type: ignore
        middleware._is_global = True

        self.add_middleware(middleware)
        return middleware
        
    def add_middleware(self, middleware: Middleware) -> None:
        if middleware.type is MiddlewareType.request:
            self.request_middlewares.append(middleware)
        else:
            self.response_middlewares.append(middleware)

    def request_middleware(self, callback: RequestMiddleware) -> Middleware:
        """
        A decorator for registering a middleware callback.

        Parameters
        ----------
        func: Callable[..., Coroutine[Any, Any, Any]]
            The middleware callback.

        """
        return self._add_middleware(MiddlewareType.request, callback)

    def remove_request_middleware(self, middleware: Middleware) -> None:
        """
        Removes a middleware from the router.

        Parameters
        ----------
        middleware: :class:`~subway.objects.Middleware`
            The middleware to remove.
        """
        return self.request_middlewares.remove(middleware)

    def response_middleware(self, callback: ResponseMiddleware) -> Middleware:
        """
        A decorator for registering a middleware callback.

        Parameters
        ----------
        func: Callable[..., Coroutine[Any, Any, Any]]
            The middleware callback.

        """
        return self._add_middleware(MiddlewareType.response, callback)

    def remove_response_middleware(self, middleware: Middleware) -> None:
        """
        Removes a middleware from the router.

        Parameters
        ----------
        middleware: :class:`~subway.objects.Middleware`
            The middleware to remove.
        """
        return self.response_middlewares.remove(middleware)

    def create_route(
        self, 
        callback: Union[Callable[..., Any], Route], 
        path: str, 
        method: str,
        *,
        name: Optional[str]
    ) -> Route:
        """
        Creates a route based off a callback or another route.

        Parameters
        ----------
        callback: Union[Callable, :class:`~subway.objects.Route`]
            The callback or route to create the route from.
        path: :class:`str`
            The path of the route.
        method: :class:`str`
            The method of the route.
        name: Optional[:class:`str`]
        """
        if isinstance(callback, Route):
            route = copy.copy(callback)

            route.path = path
            route.method = method

            if name is not None:
                route.name = name
        else:
            route = Route(path, method, callback, router=self, name=name)

        route.raw_path = self.url_prefix + route.path
        route.path = route.raw_path

        return route

    def create_websocket_route(
        self, 
        callback: Union[Callable[..., Any], WebSocketRoute], 
        path: str,
        *,
        name: Optional[str]
    ) -> WebSocketRoute:
        """
        Creates a websocket route.

        Parameters
        ----------
        path: :class:`str`
            The path of the route.
        callback: Union[Callable, :class:`~subway.objects.WebSocketRoute`]
            The callback of the route.
        name: Optional[:class:`str`]
        """
        if isinstance(callback, WebSocketRoute):
            route = copy.copy(callback)
            route.path = path

            if name is not None:
                route.name = name
        else:
            route = WebSocketRoute(path, 'GET', callback, router=self, name=name)

        route.raw_path = self.url_prefix + route.path
        route.path = route.raw_path

        return route

    def __iter__(self):
        return self.routes.values().__iter__()
