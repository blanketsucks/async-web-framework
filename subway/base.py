from __future__ import annotations

from typing import Callable, Literal, Optional, Union, overload, TYPE_CHECKING, Any
from abc import ABC, abstractmethod

from .types import CoroFunc, ResponseMiddleware, RequestMiddleware
from .router import Router
from .objects import Listener, Middleware, Route, WebSocketRoute, MiddlewareType
from .errors import RegistrationError

if TYPE_CHECKING:
    RouteDecorator = Callable[..., Route]
    WebSocketRouteDecorator = Callable[[Union[CoroFunc[Any], WebSocketRoute]], WebSocketRoute]

__all__ = 'BaseApplication',

class BaseApplication(ABC):
    router: Router

    @abstractmethod
    def add_event_listener(self, callback: CoroFunc[Any], name: str) -> Listener:
        raise NotImplementedError

    @abstractmethod
    def remove_event_listener(self, listener: Listener) -> Any:
        raise NotImplementedError

    def event(self, name: Optional[str] = None) -> Callable[[CoroFunc[Any]], Listener]:
        """
        A decorator that adds an event listener to the application.

        Parameters
        ----------
        name: :class:`str`
            The name of the event to listen for, if nothing was passed in the name of the function is used.

        Example
        ----------
        .. code-block :: python3

            @event('on_startup')
            async def startup():
                print('Application started serving')
            
        Returns
        -------
        :class:`~.Listener`
        """
        def decorator(callback: CoroFunc[Any]) -> Listener:
            return self.add_event_listener(callback, name or callback.__name__)
        return decorator

    @overload
    def add_route(
        self,
        callback: Union[CoroFunc[Any], Route],
        path: str,
        method: str,
    ) -> Route:
        ...
    @overload
    def add_route(
        self,
        callback: Union[CoroFunc[Any], Route],
        path: str,
        method: str,
        *,
        websocket: Literal[False],
        name: Optional[str] = None
    ) -> Route:
        ...
    @overload
    def add_route(
        self,
        callback: Union[CoroFunc[Any], WebSocketRoute],
        path: str,
        method: str,
        *,
        websocket: Literal[True],
        name: Optional[str] = None
    ) -> WebSocketRoute:
        ...
    def add_route(
        self,
        callback: Union[CoroFunc[Any], Route, WebSocketRoute],
        path: str,
        method: str,
        *,
        websocket: bool = False,
        name: Optional[str] = None
    ) -> Union[Route, WebSocketRoute]:
        """Creates and adds a route to the router.

        Parameters
        ----------
        callback: Union[Callable, :class:`~.Route`]
            The callback/route to register the route with.
        path: :class:`str`
            The path of the route.
        method: :class:`str`
            The HTTP method of the route.
        websocket: :class:`bool`
            Whether the route is a websocket route.
        name: Optional[:class:`str`]
            The name of the route.
        """
        if websocket:
            route = self.router.create_websocket_route(callback, path, name=name)
        else:
            route = self.router.create_route(callback, path, method, name=name)

        return self.router.add_route(route)

    def route(self, path: str, method: Optional[str] = None, *, name: Optional[str] = None) -> RouteDecorator:
        """Registers a route.

        Parameters
        ----------
        path: :class:`str`
            The path of the route
        method: Optional[:class:`str`]
            The HTTP method of the route. Defaults to ``GET``.
        name: Optional[:class:`str`]
            The name of the route.

        Examples
        -------

        .. code-block :: python3

            @route('/', 'GET')
            async def index(request: subway.Request):
                return 'Hello, world!'

        """
        method = method or 'GET'
        def decorator(callback: Union[CoroFunc[Any], Route]) -> Route:
            return self.add_route(callback, path, method, websocket=False, name=name)
        return decorator

    def websocket(self, path: str, *, name: Optional[str] = None) -> WebSocketRouteDecorator:
        """Registers a websocket route.

        Parameters
        ----------
        path: :class:`str`
            The path to register the route for.
        name: Optional[:class:`str`]
            The name of the route.

        Examples
        -------

        .. code-block :: python3

            @websocket('/ws')
            async def websocket_handler(request: subway.Request, ws: subway.WebSocket):
                await ws.send(b'Hello, World')

                data = await ws.receive()
                print(data.data)

                await ws.close()

        Returns
        -------
        :class:`~.Route`
        """
        def decorator(callback: Union[CoroFunc[Any], Route]) -> WebSocketRoute:
            return self.add_route(callback, path, 'GET', websocket=True, name=name)
        return decorator

    def get(self, path: str, *, name: Optional[str] = None) -> RouteDecorator:
        """
        Adds a route that handles GET requests.

        Parameters
        ----------
        path: :class:`str`
            The path of the route.
        name: Optional[:class:`str`]
            The name of the route.

        Returns
        -------
        :class:`~.Route`
        """
        return self.route(path, 'GET', name=name)

    def post(self, path: str, *, name: Optional[str] = None) -> RouteDecorator:
        """
        Adds a route that handles POST requests.

        Parameters
        ----------
        path: :class:`str`
            The path of the route.
        name: Optional[:class:`str`]
            The name of the route.

        Returns
        -------
        :class:`~.Route`
        """
        return self.route(path, 'POST', name=name)

    def put(self, path: str, *, name: Optional[str] = None) -> RouteDecorator:
        """
        Adds a route that handles PUT requests.

        Parameters
        ----------
        path: :class:`str`
            The path of the route.
        name: Optional[:class:`str`]
            The name of the route.

        Returns
        -------
        :class:`~.Route`
        """
        return self.route(path, 'PUT', name=name)

    def delete(self, path: str, *, name: Optional[str] = None) -> RouteDecorator:
        """
        Adds a route that handles DELETE requests.

        Parameters
        ----------
        path: :class:`str`
            The path of the route.
        name: Optional[:class:`str`]
            The name of the route.

        Returns
        -------
        :class:`~.Route`
        """
        return self.route(path, 'DELETE', name=name)

    def patch(self, path: str, *, name: Optional[str] = None) -> RouteDecorator:
        """
        Adds a route that handles PATCH requests.

        Parameters
        ----------
        path: :class:`str`
            The path of the route.
        name: Optional[:class:`str`]
            The name of the route.

        Returns
        -------
        :class:`~.Route`
        """
        return self.route(path, 'PATCH', name=name)

    def options(self, path: str, *, name: Optional[str] = None) -> RouteDecorator:
        """
        Adds a route that handles OPTIONS requests.

        Parameters
        ----------
        path: :class:`str`
            The path of the route.
        name: Optional[:class:`str`]
            The name of the route.

        Returns
        -------
        :class:`~.Route`
        """
        return self.route(path, 'OPTIONS', name=name)

    def head(self, path: str, *, name: Optional[str] = None) -> RouteDecorator:
        """
        Adds a route that handles HEAD requests.

        Parameters
        ----------
        path: :class:`str`
            The path of the route.
        name: Optional[:class:`str`]
            The name of the route.

        Returns
        -------
        :class:`~.Route`
        """
        return self.route(path, 'HEAD', name=name)

    def request_middleware(self, callback: RequestMiddleware) -> Middleware:
        """Adds a request middleware to the application.

        Middlewares must return a boolean value or raise an error

        Parameters
        ----------
        callback: Callable
            The middleware to add.

        Returns
        -------
        :class:`~.Middleware`
            The middleware that was added.

        Example
        -------
        .. code-block :: python3

            @request_middleware
            async def middleware(route: Route, request: Request, **kwargs):
                print('Middleware ran')
                return True

        """
        return self.router.request_middleware(callback)

    def remove_request_middleware(self, middleware: Middleware) -> None:
        self.router.remove_request_middleware(middleware)

    def response_middleware(self, callback: ResponseMiddleware) -> Middleware:
        """Adds a response middleware to the application.

        Middlewares must return a boolean value or raise an error

        Parameters
        ----------
        callback: Callable
            The middleware to add.

        Returns
        -------
        :class:`~.Middleware`
            The middleware that was added.

        Example
        -------
        .. code-block :: python3

            @response_middleware
            async def middleware(route: Route, request: Request, response: Response, **kwargs):
                print('Middleware ran')
                return True

        """
        return self.router.response_middleware(callback)

    def remove_response_middleware(self, middleware: Middleware) -> None:
        self.router.remove_response_middleware(middleware)

    @overload
    def middleware(self, type: Literal[MiddlewareType.request]) -> Callable[[RequestMiddleware], Middleware]:
        ...
    @overload
    def middleware(self, type: Literal[MiddlewareType.response]) -> Callable[[ResponseMiddleware], Middleware]:
        ...
    def middleware(self, type: MiddlewareType) -> Any:
        """
        Adds a middleware to the application.

        Middlewares must return a boolean value or raise an error

        Parameters
        ----------
        type: :class:`str`
            The type of middleware to add.

        Example
        -------
        .. code-block :: python3

            @middleware(MiddlewareType.request)
            async def middleware(route: Route, request: Request, **kwargs):
                print('Middleware ran')
                return True

        """
        if type is MiddlewareType.request:
            return self.request_middleware
        else:
            return self.response_middleware
