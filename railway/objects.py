from __future__ import annotations

from typing import TYPE_CHECKING, Callable, List, Any, Optional, Dict, Union, NoReturn
import inspect
import re

from .types import CoroFunc, Coro
from .responses import HTTPException
from .response import Response
from .request import Request
from .errors import RegistrationError
from . import utils

if TYPE_CHECKING:
    from .router import Router
    from .resources import Resource

__all__ = (
    'Object',
    'Route',
    'PartialRoute',
    'WebSocketRoute',
    'Middleware',
    'Listener',
    'route',
    'websocket_route',
    'listener',
    'middleware',
)

class Object:
    """
    A base object.

    Parameters
    ----------
    callback: Callable[..., Coroutine[Any, Any, Any]]]
        the function used by the object.

    Attributes
    ----------
    callback: Callable[..., Coroutine[Any, Any, Any]]]
        The coroutine function used by the object.
    """
    callback: CoroFunc[Any]

    def __init__(self, callback: CoroFunc) -> None:
        self.callback = callback

    async def __call__(self, *args: Any, **kwds: Any) -> Any:
        return await self.callback(*args, **kwds)

class PartialRoute:
    """
    A partial route. This object is created whenever an error occurs during the route handling process.

    Parameters
    ----------
    path: :class:`str`
        The part of the route.
    method: :class:`str`
        The method of the route.

    Attributes
    ----------
    path: 
        The path of the route.
    method: 
        The method of the route.
    """
    def __init__(self, path: str, method: str) -> None:
        self.path: str = path
        self.method: str = method

    def __repr__(self) -> str:
        return f'<PartialRoute path={self.path!r} method={self.method!r}>'

class Route(Object):
    """
    A route object.

    Parameters
    ----------
    path: :class:`str`
        The path of the route.
    method: :class:`str`
        The method of the route.
    callback: Callable[..., Coroutine[Any, Any, Any]]
        The function used by the route.
    router: Optional[:class:`~railway.router.Router`]
        The router to register the route with.
        The case that this can be ``None`` is when using :func:`~railway.objects.route`.

    Attributes
    ----------
    path: :class:`str`
        The path of the route.
    method: :class:`str`
        The method of the route.
    callback:  Callable[..., Coroutine[Any, Any, Any]]
        The coroutine function used by the route.
    """
    __cache_control__: Dict[str, Any]

    def __init__(
        self, 
        path: str, 
        method: str, 
        callback: CoroFunc,
        *, 
        name: Optional[str] = None,
        router: Optional['Router']
    ) -> None:
        if hasattr(callback, '__cache_control__'):
            self.__cache_control__ = callback.__cache_control__

        self._router = router

        self.path: str = path
        self.method: str = method
        self.callback = callback
        self.name = name or callback.__name__.replace('_', ' ').title()
        self.raw_path: str = None # type: ignore
        self.parent: Optional[Resource] = None

        self._error_handler = None
        self._status_code_handlers: Dict[int, Callable[..., Coro[Any]]] = {}
        self._middlewares: List[Middleware] = []
        self._response_middlewares: List[Callable[[Request, Response, Route], Coro[Any]]] = []
        self._after_request = None

        self.__doc__ = inspect.getdoc(callback)

    async def dispatch(
        self, 
        request: Request, 
        exc: Exception
    ) -> bool:
        if isinstance(exc, HTTPException):
            callback = self._status_code_handlers.get(exc.status)
            if callback:
                if self.parent:
                    response = await callback(self.parent, request, exc, self)
                else:
                    response = await callback(request, exc, self)

                await request.send(response)
                return True

        if self._error_handler:
            if self.parent:
                response = await self._error_handler(self.parent, request, exc, self)
            else:
                response = await self._error_handler(request, exc, self)

            await request.send(response)
            return True

        return False

    @property
    def signature(self) -> inspect.Signature:
        """
        The signature of the route.
        """
        return inspect.signature(self.callback)

    @property
    def middlewares(self) -> List[Middleware]:
        """
        A list of middlewares registered with the route.
        """
        return self._middlewares

    @property
    def response_middlewares(self) -> List[Callable[[Request, Response, Route], Coro[Any]]]:
        """
        A list of response middlewares registered with the route.
        """
        return self._response_middlewares

    @property
    def router(self) -> Optional['Router']:
        """
        The router used to register the route with.
        """
        return self._router

    def is_websocket(self) -> bool:
        """
        Checks if the route is a websocket route.
        """
        return isinstance(self, WebSocketRoute)

    def match(self, path: str) -> Optional[Dict[str, str]]:
        """
        Matches the path with the route.

        Parameters
        ----------
        path: :class:`str`
            The path to match.
        
        Returns
        -------
        :class:`dict`
            A dictionary of the matched parameters.
        """
        match = re.fullmatch(self.path, path)
        if match:
            return match.groupdict()

        return None

    def cleanup_middlewares(self):
        """
        Clears all the middlewares registered with the route.
        """
        self._middlewares.clear()

    def add_status_code_handler(
        self, 
        status: int, 
        callback: Callable[..., Coro[Any]]
    ):
        """
        Adds a specific status code handler to the route.
        This applies to only error status codes for obvious reasons.

        Parameters
        ----------
        status: :class:`int`
            The status code to handle.
        callback: Callable[[:class:`~railway.objects.Request`, :class:`~railway.exceptions.HTTPException`, :class:`~railway.objects.Route`], Coro]
            The callback to handle the status code.
        """
        if not utils.iscoroutinefunction(callback):
            raise RegistrationError('Status code handlers must be coroutine functions')

        self._status_code_handlers[status] = callback
        return callback

    def remove_status_code_handler(self, status: int):
        """
        Removes a status code handler from the route.

        Parameters
        ----------
        status: :class:`int`
            The status code to remove.
        """
        callback = self._status_code_handlers.pop(status, None)
        return callback

    def status_code_handler(self, status: int):
        """
        A decorator that adds a status code handler to the route.
        The handler function MUST return something.

        Parameters
        ----------
        status: :class:`int`
            The status code to handle.

        Example
        ---------
        .. code-block :: python3

            import railway

            app = railway.Application()
            app.users = {}

            @app.route('/users/{id}', 'GET')
            async def get_user(request: railway.Request, id: int):
                user = app.users.get(id)
                if not user:
                    raise railway.NotFound()

                return user

            @get_user.status_code_handler(404)
            async def handle_404(
                request: railway.Request, 
                exception: railway.HTTPException, 
                route: railway.Route
            ):
                return {
                        'message': 'User not found.',
                        'status': 404
                        }

            app.run()
        
        """
        def decorator(func: Callable[..., Coro[Any]]):
            return self.add_status_code_handler(status, func)
        return decorator

    def on_error(self, callback: Callable[..., Coro[Any]]):
        """
        Registers an error handler for the route.
        The handler function MUST return something.

        Parameters
        ----------
        callback: Callable[[:class:`~.Request`, :class:`~.HTTPException`, :class:`~.Route`], Coro]
            The callback to handle errors.
        """
        if not utils.iscoroutinefunction(callback):
            raise RegistrationError('Error handlers must be coroutine functions')

        self._error_handler = callback
        return callback

    def add_middleware(self, callback: CoroFunc[Union[bool, NoReturn]]) -> Middleware:
        """
        Registers a middleware with the route.

        Parameters
        ----------
        callback: Callable[..., Coroutine[Any, Any, Any]]
            The coroutine function used by the middleware.
        """
        if not utils.iscoroutinefunction(callback):
            raise RegistrationError('All middlewares must be coroutine functions')

        middleware = Middleware(callback, route=self)
        self._middlewares.append(middleware)

        return middleware

    def remove_middleware(self, middleware: Middleware) -> Middleware:
        """
        Removes a middleware from the route.

        Parameters
        ----------
            middleware: :class:`~railway.objects.Middleware`
                The middleware to remove.
        """
        self._middlewares.remove(middleware)
        return middleware

    def middleware(self, callback: CoroFunc[Union[bool, NoReturn]]) -> Middleware:
        """
        A decorator that registers a middleware with the route.

        Parameters
        ----------
        callback: Callable
            The coroutine function used by the middleware.

        Example
        --------
        .. code-block:: python3

            import railway

            app = railway.Application()

            @app.route('/')
            async def index(request: railway.Request):
                return 'Hello, world!'

            @index.middleware
            async def middleware(route: railway.Route, request: railway, **kwargs):
                print('Middleware called')

            app.run()

        """
        return self.add_middleware(callback)

    def add_response_middleware(
        self, callback: Callable[[Request, Response, Route], Coro[Any]]
    ) -> Callable[[Request, Response, Route], Coro[Any]]:
        """
        Registers a response middleware with the route.

        Parameters
        ----------
        callback: Callable[..., Any]
            The coroutine function used by the middleware.
        """
        if not utils.iscoroutinefunction(callback):
            raise RegistrationError('Response middlewares must be coroutine functions')

        self._response_middlewares.append(callback)
        return callback

    def remove_response_middleware(
        self, callback: Callable[[Request, Response, Route], Coro[Any]]
    ) -> Callable[[Request, Response, Route], Coro[Any]]:
        """
        Removes a response middleware from the route.

        Parameters
        ----------
        callback: Callable[..., Any]
            The coroutine function used by the middleware.
        """
        self._response_middlewares.remove(callback)
        return callback

    def response_middleware(
        self, callback: Callable[[Request, Response, Route], Coro[Any]]
    ) -> Callable[[Request, Response, Route], Coro[Any]]:
        """
        A decorator that registers a response middleware with the route.

        Parameters
        ----------
        callback: Callable[..., Any]
            The coroutine function used by the middleware.

        Example
        --------
        .. code-block:: python3

            import railway

            app = railway.Application()

            @app.route('/')
            async def index(request: railway.Request):
                return 'Hello, world!'

            @index.response_middleware
            async def middleware(request: railway.Request, response: railway.Response, route: railway.Route):
                print('Middleware called')

            app.run()

        """
        return self.add_response_middleware(callback)

    def after_request(self, callback: CoroFunc) -> CoroFunc:
        """
        Registers a callback to be called after the route is handled.

        Parameters
        ----------
            callback: Callable[..., Coroutine[Any, Any, Any]]]
                The coroutine function or a function to be called.
        """
        if not utils.iscoroutinefunction(callback):
            raise RegistrationError('After request callbacks must be coroutine functions')

        self._after_request = callback
        return callback

    def destroy(self):
        """
        Destroys the route.
        """
        self.clear()

        if not self._router:
            return

        self._router.remove_route(self)
        return self

    def clear(self):
        """
        Clears the route's attached callbacks.
        """
        self._after_request = None
        self._error_handler = None
        self._middlewares.clear()
        self._status_code_handlers.clear()

    def __call__(self, *args, **kwargs) -> Any:
        return self.callback(*args, **kwargs)

    def __repr__(self) -> str:
        return '<Route path={0.path!r} method={0.method!r}>'.format(self)

class Middleware(Object):
    """
    A middleware object.

    Parameters
    ----------
    callback: Callable[..., Coroutine[Any, Any, Any]]]
        The coroutine function used by the middleware.
    route: Optional[:class:`~railway.objects.Route`]
        The route to register the middleware with.
    router: Optional[:class:`~railway.router.Router`]
        The router to register the middleware with.

    Attributes
    ----------
    callback: Callable[..., Coroutine[Any, Any, Any]]]
        The coroutine(?) function used by the middleware.
    """
    def __init__(self, callback: CoroFunc[Union[bool, NoReturn]], route: Optional[Route]=None, router: Optional['Router']=None) -> None:
        self.callback = callback

        self._router = router
        self._route = route

        self._is_global = False

    @property
    def router(self) -> Optional[Router]:
        """
        The router used to register the middleware with.
        """
        return self._router

    @router.setter
    def router(self, value):
        if not isinstance(value, Router):
            raise TypeError('router must be a Router instance')

        self._router = value

    @property
    def route(self) -> Optional['Route']:
        """
        The route used to register the middleware with.
        """
        return self._route

    @route.setter
    def route(self, value):
        if not isinstance(value, Route):
            raise TypeError('route must be a Route instance')

        self._route = value
        self.attach(value)

    @route.deleter
    def route(self):
        self.detach()

    def is_global(self) -> bool:
        """
        True if the middleware is registered with the global router.
        """
        return self._is_global

    def is_route_specific(self) -> bool:
        """
        True if the middleware is registered with a route.
        """
        return not self.is_global()

    def detach(self):
        """
        Detaches the middleware from the router.
        """
        if self._route:
            self._route.remove_middleware(self)
            self._route = None

            if self._router:
                self._router.middleware(self.callback)

        return self

    def attach(self, route: Route):
        """
        Attaches the middleware to a route.

        Parameters
        ----------
        route: :class:`~railway.objects.Route`
            The route to attach the middleware to.
        """
        if self.is_global():
            raise RegistrationError('Global middlewares can not be attached to a route')

        self.route = route

        if self._router:
            self._router.middleware(self.callback)

    async def __call__(self, route: Route, request: Request, **kwargs: Any) -> Any:
        return await super().__call__(route, request, **kwargs)

    def __repr__(self) -> str:
        return f'<Middleware is_global={self.is_global()!r}>'

class WebSocketRoute(Route):
    """
    A subclass of :class:`~railway.objects.Route` representing a websocket route
    """
    pass

class Listener(Object):
    """
    A listener object.

    Parameters
    ----------
    callback: Callable[..., Coroutine[Any, Any, Any]]
        The coroutine function used by the listener.
    event: :class:`str`
        The event the listener is registered to.

    Attributes
    ----------
    callback: Callable[..., Coroutine[Any, Any, Any]]
        The coroutine function used by the listener.
    event: :class:`str`
        The event the listener is registered to.
    """
    def __init__(self, callback: CoroFunc[Any], name: str) -> None:
        self.event: str = name
        self.callback = callback

    def __repr__(self) -> str:
        return '<Listener event={0.event!r}>'.format(self)

def route(path: str, method: str, *, name: Optional[str]=None) -> Callable[[CoroFunc], Route]:
    """
    A decorator that returns a :class:`~railway.objects.Route` object.

    Parameters
    ----------
    path: :class:`str`
        The path to register the route with.
    method: :class:`str`
        The HTTP method to register the route with.
    """
    def decorator(func: CoroFunc) -> Route:
        route = Route(path, method, func, name=name, router=None)
        route.raw_path = path

        return route
    return decorator

def websocket_route(path: str, *, name: Optional[str] = None) -> Callable[[CoroFunc], WebSocketRoute]:
    """
    A decorator that returns a :class:`~railway.objects.WebSocketRoute` object.

    Parameters
    ----------
    path: :class:`str`
        The path to register the route with.
    """
    def decorator(func: CoroFunc) -> WebSocketRoute:
        return WebSocketRoute(path, 'GET', func, name=name, router=None)
    return decorator

def listener(event: str = None) -> Callable[[CoroFunc], Listener]:
    """
    A decorator that returns a :class:`~railway.objects.Listener` object.

    Parameters
    ----------
    event: :class:`str`
        The event to register the listener to.
    """
    def decorator(func: CoroFunc) -> Listener:
        return Listener(func, event or func.__name__)
    return decorator

def middleware(callback: CoroFunc[Union[bool, NoReturn]]) -> Middleware:
    """
    A decorator that returns a global :class:`~railway.objects.Middleware` object.

    Parameters:
        callback: CoroFunc
            The coroutine(?) function used by the middleware.
    """
    middleware = Middleware(callback)
    middleware._is_global = True

    return middleware