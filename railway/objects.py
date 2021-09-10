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
from __future__ import annotations
import functools
from typing import TYPE_CHECKING, Callable, List, Any, Optional, Union
import inspect

from ._types import CoroFunc, Func, MaybeCoroFunc
from .utils import maybe_coroutine
from .errors import RegistrationError

if TYPE_CHECKING:
    from .router import Router

__all__ = (
    'Object',
    'Route',
    'PartialRoute',
    'WebsocketRoute',
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
    callback: Union[Callable[..., Any], Callable[..., Coroutine[Any, Any, Any]]]
        the function used by the object.

    Attributes
    ----------
    callback: Union[Callable[..., Any], Callable[..., Coroutine[Any, Any, Any]]]
        The coroutine(?) function used by the object.
    """
    callback: MaybeCoroFunc

    def __init__(self, callback: MaybeCoroFunc) -> None:
        self.callback = callback

    async def __call__(self, *args: Any, **kwds: Any) -> Any:
        return await maybe_coroutine(self.callback, *args, **kwds)

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
    callback: Union[Callable[..., Any], Callable[..., Coroutine[Any, Any, Any]]]
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
    callback: Union[Callable[..., Any], Callable[..., Coroutine[Any, Any, Any]]]
        The coroutine(?) function used by the route.
    """
    def __init__(self, path: str, method: str, callback: MaybeCoroFunc, *, router: Optional['Router']) -> None:
        self._router = router

        self.path: str = path
        self.method: str = method
        self.callback: MaybeCoroFunc = callback

        self._middlewares: List[Middleware] = []
        self._after_request = None

    @property
    def middlewares(self) -> List[Middleware]:
        """
        A list of middlewares registered with the route.
        """
        return self._middlewares

    @property
    def router(self) -> 'Router':
        """
        The router used to register the route with.
        """
        return self._router

    def cleanup_middlewares(self):
        """
        Clears all the middlewares registered with the route.
        """
        self._middlewares.clear()

    def add_middleware(self, callback: CoroFunc) -> Middleware:
        """
        Registers a middleware with the route.

        Parameters
        ----------
            callback: Callable[..., Coroutine[Any, Any, Any]]
                The coroutine function used by the middleware.

        """
        if not inspect.iscoroutinefunction(callback):
            raise RegistrationError('All middlewares must be async')

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

    def middleware(self, callback: CoroFunc) -> Middleware:
        """
        A decorator that registers a middleware with the route.

        Parameters
        ----------
            callback: Callable[..., Coroutine[Any, Any, Any]]
                The coroutine function used by the middleware.
        """
        return self.add_middleware(callback)

    def after_request(self, callback: MaybeCoroFunc) -> MaybeCoroFunc:
        """
        Registers a callback to be called after the route is handled.

        Parameters
        ----------
            callback: Union[Callable[..., Any], Callable[..., Coroutine[Any, Any, Any]]]
                The coroutine(?) function or a function to be called.
        """
        self._after_request = callback
        return callback

    def destroy(self):
        """
        Destroys the route.
        """
        if not self._router:
            return

        self._router.remove_route(self)
        return self

    def __repr__(self) -> str:
        return '<Route path={0.path!r} method={0.method!r}>'.format(self)

class Middleware(Object):
    """
    A middleware object.

    Parameters
    ----------
    callback: CoroFunc
        The coroutine(?) function used by the middleware.
    route: Optional[:class:`~railway.objects.Route`]
        The route to register the middleware with.
    router: Optional[:class:`~railway.router.Router`]
        The router to register the middleware with.

    Attributes
    ----------
    callback: CoroFunc
        The coroutine(?) function used by the middleware.
    """
    def __init__(self, callback: CoroFunc, route: Optional[Route]=None, router: Optional['Router']=None) -> None:
        self.callback: CoroFunc = callback

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
            self._route.remove_middleware(self.callback)
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

    def __repr__(self) -> str:
        return f'<Middleware is_global={self.is_global()!r}>'

class WebsocketRoute(Route):
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
            The coroutine(?) function used by the listener.
        event: :class:`str`
            The event the listener is registered to.

    Attributes
    ----------
        callback: Callable[..., Coroutine[Any, Any, Any]]
            The coroutine(?) function used by the listener.
        event: :class:`str`
            The event the listener is registered to.
    """
    def __init__(self, callback: CoroFunc, name: str) -> None:
        self.event: str = name
        self.callback: CoroFunc = callback

    def __repr__(self) -> str:
        return '<Listener event={0.event!r}>'.format(self)

def route(path: str, method: str) -> Callable[[CoroFunc], Route]:
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
        
        if getattr(func, '__self__', None):
            func = functools.partial(func, func.__self__)

        return Route(path, method, func, router=None)
    return decorator

def websocket_route(path: str) -> Callable[[CoroFunc], WebsocketRoute]:
    """
    A decorator that returns a :class:`~railway.objects.WebsocketRoute` object.

    Parameters
    ----------
    path: :class:`str`
        The path to register the route with.
    
    """
    def decorator(func: CoroFunc) -> WebsocketRoute:
        return WebsocketRoute(path, 'GET', func, router=None)
    return decorator

def listener(event: str=None) -> Callable[[CoroFunc], Listener]:
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

def middleware(callback: CoroFunc) -> Middleware:
    """
    A decorator that returns a global :class:`~railway.objects.Middleware` object.

    Parameters:
        callback: CoroFunc
            The coroutine(?) function used by the middleware.
    """
    middleware = Middleware(callback)
    middleware._is_global = True

    return middleware