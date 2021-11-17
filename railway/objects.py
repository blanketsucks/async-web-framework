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
from typing import TYPE_CHECKING, Callable, List, Any, Optional, Dict
import inspect
import asyncio

from ._types import CoroFunc, MaybeCoroFunc, Coro
from .responses import HTTPException
from .request import Request
from .errors import RegistrationError
from .locks import _MaybeSemaphore, Semaphore

if TYPE_CHECKING:
    from .router import Router
    from .injectables import Injectable

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

async def _call(func: CoroFunc, parent: Optional[Injectable], *args: Any, **kwargs: Any):
    if parent:
        return await func(parent, *args, **kwargs)

    return await func(*args, **kwargs)

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
    callback: CoroFunc

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
    def __init__(self, path: str, method: str, callback: CoroFunc, *, router: Optional['Router']) -> None:
        self._router = router

        self.path: str = path
        self.method: str = method
        self.callback = callback
        self.parent: Optional[Injectable] = None

        self._error_handler = None
        self._status_code_handlers: Dict[int, Callable[[Request, HTTPException, Route], Coro]] = {}
        self._middlewares: List[Middleware] = []
        self._after_request = None
        self._limiter = _MaybeSemaphore(None)

    async def _dispatch_error(self, request: Request, exc: Exception):
        if isinstance(exc, HTTPException):
            callback = self._status_code_handlers.get(exc.status)
            if callback:
                response = await _call(callback, self.parent, request, exc, self)
                await request.send(response)

                return True

        if self._error_handler:
            await _call(self._error_handler, self.parent, request, exc, self)
            return True

        return False

    def is_websocket(self) -> bool:
        return isinstance(self, WebsocketRoute)

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
    def router(self) -> Optional['Router']:
        """
        The router used to register the route with.
        """
        return self._router

    def cleanup_middlewares(self):
        """
        Clears all the middlewares registered with the route.
        """
        self._middlewares.clear()

    def add_status_code_handler(
        self, 
        status: int, 
        callback: Callable[[Request, HTTPException, Route], Coro]
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
        if not inspect.iscoroutinefunction(callback):
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
        def decorator(func: Callable[[Request, HTTPException, Route], Coro]):
            return self.add_status_code_handler(status, func)
        return decorator

    def on_error(self, callback: Callable[[Request, Exception, Route], Coro]):
        """
        Registers an error handler for the route.

        Parameters
        ----------
        callback: Callable[[:class:`~.Request`, :class:`~.HTTPException`, :class:`~.Route`], Coro]
            The callback to handle errors.
        """
        if not inspect.iscoroutinefunction(callback):
            raise RegistrationError('Error handlers must be coroutine functions')

        self._error_handler = callback
        return callback

    def add_middleware(self, callback: CoroFunc) -> Middleware:
        """
        Registers a middleware with the route.

        Parameters
        ----------
        callback: Callable[..., Coroutine[Any, Any, Any]]
            The coroutine function used by the middleware.
        """
        if not inspect.iscoroutinefunction(callback):
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

    def middleware(self, callback: CoroFunc) -> Middleware:
        """
        A decorator that registers a middleware with the route.

        Parameters
        ----------
            callback: Callable[..., Coroutine[Any, Any, Any]]
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
            async def middleware(request: railway.Request, route: railway.Route, **kwargs):
                print('Middleware called')

            app.run()

        """
        return self.add_middleware(callback)

    def after_request(self, callback: CoroFunc) -> CoroFunc:
        """
        Registers a callback to be called after the route is handled.

        Parameters
        ----------
            callback: Callable[..., Coroutine[Any, Any, Any]]]
                The coroutine function or a function to be called.
        """
        if not inspect.iscoroutinefunction(callback):
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

    def add_semaphore(self, semaphore: Semaphore):
        """
        Adds a semaphore to the route that can be used to limit the number of concurrent requests.

        Parameters
        ----------
        semaphore: Union[:class:`asyncio.Semaphore`, :class:`~railway.locks.Semaphore`]
            A semaphore. This can be either from the :mod:`asyncio` module or the :mod:`railway.locks` module.

        Example
        --------
        .. code-block:: python3 

            import railway

            app = railway.Application()
            sem = railway.Semaphore(50)

            @app.route('/')
            async def index(request: railway.Request):
                return 'pog'

            index.add_semaphore(sem)

            app.run()

        """
        if not isinstance(semaphore, (Semaphore, asyncio.Semaphore)):
            raise TypeError('semaphore must be an instance of asyncio.Semaphore or railway.Semaphore')

        self._limiter.semaphore = semaphore

    def remove_semaphore(self):
        """
        Removes the semaphore from the route.
        """
        self._limiter.semaphore = None

    async def __call__(self, *args: Any, **kwds: Any) -> Any:
        async with self._limiter:
            return await _call(self.callback, self.parent, *args, **kwds)

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
    def __init__(self, callback: CoroFunc, route: Optional[Route]=None, router: Optional['Router']=None) -> None:
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
    def __init__(self, callback: CoroFunc, name: str) -> None:
        self.event: str = name
        self.callback = callback

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