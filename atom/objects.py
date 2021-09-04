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
    callback: MaybeCoroFunc

    def __init__(self, callback: MaybeCoroFunc) -> None:
        self.callback = callback

    async def __call__(self, *args: Any, **kwds: Any) -> Any:
        return await maybe_coroutine(self.callback, *args, **kwds)

class PartialRoute:
    def __init__(self, path: str, method: str) -> None:
        self.path = path
        self.method = method

    def __repr__(self) -> str:
        return f'<PartialRoute path={self.path!r} method={self.method!r}>'

class Route(Object):
    def __init__(self, path: str, method: str, callback: MaybeCoroFunc, *, router: Optional[Router]) -> None:
        self._router = router

        self.path = path
        self.method = method
        self.callback = callback

        self._middlewares: List[Middleware] = []
        self._after_request = None

    @property
    def middlewares(self):
        return self._middlewares

    @property
    def router(self):
        return self._router

    def cleanup_middlewares(self):
        self._middlewares.clear()

    def add_middleware(self, callback: CoroFunc) -> Middleware:
        if not inspect.iscoroutinefunction(callback):
            raise RegistrationError('All middlewares must be async')

        middleware = Middleware(callback, route=self)
        self._middlewares.append(middleware)

        return middleware

    def remove_middleware(self, middleware: Middleware) -> Middleware:
        self._middlewares.remove(middleware)
        return middleware

    def middleware(self, callback: CoroFunc) -> Middleware:
        return self.add_middleware(callback)

    def after_request(self, callback: Union[CoroFunc, Func]):
        self._after_request = callback
        return callback

    def destroy(self):
        if not self._router:
            return

        self._router.remove_route(self)
        return self

    def __repr__(self) -> str:
        return '<Route path={0.path!r} method={0.method!r}>'.format(self)

class Middleware(Object):
    def __init__(self, callback: CoroFunc, route: Optional[Route]=None, router: Optional[Router]=None) -> None:
        self.callback = callback

        self._router = router
        self._route = route

        self._is_global = False

    @property
    def router(self) -> Optional[Router]:
        return self._router

    @router.setter
    def router(self, value):
        if not isinstance(value, Router):
            raise TypeError('router must be a Router instance')

        self._router = value

    @property
    def route(self) -> Optional[Route]:
        return self._route

    @route.setter
    def route(self, value):
        if not isinstance(value, Route):
            raise TypeError('route must be a Route instance')

        self._route = value

    @route.deleter
    def route(self):
        self.detach()

    def is_global(self):
        return self._is_global

    def is_route_specific(self):
        return not self.is_global()

    def detach(self):
        if self._route:
            self._route.remove_middleware(self.callback)
            self._route = None

            if self._router:
                self._router.middleware(self.callback)

        return self

    def attach(self, route: Route):
        if self.is_global():
            raise RegistrationError('Global middlewares can not be attached to a route')

        self.route = route

        if self._router:
            self._router.middleware(self.callback)

    def __repr__(self) -> str:
        return f'<Middleware is_global={self.is_global()!r}>'

class WebsocketRoute(Route):
    pass

class Listener(Object):
    def __init__(self, callback: CoroFunc, name: str) -> None:
        self.event = name
        self.callback = callback

    def __repr__(self) -> str:
        return '<Listener event={0.event!r}>'.format(self)

def route(path: str, method: str) -> Callable[[CoroFunc], Route]:
    def decorator(func: CoroFunc) -> Route:
        
        if getattr(func, '__self__', None):
            func = functools.partial(func, func.__self__)

        return Route(path, method, func, router=None)
    return decorator

def websocket_route(path: str, method: str) -> Callable[[CoroFunc], WebsocketRoute]:
    def decorator(func: CoroFunc) -> WebsocketRoute:
        return WebsocketRoute(path, method, func)
    return decorator

def listener(event: str=None) -> Callable[[CoroFunc], Listener]:
    def decorator(func: CoroFunc) -> Listener:
        return Listener(func, event or func.__name__)
    return decorator

def middleware(callback: CoroFunc) -> Middleware:
    middleware = Middleware(callback)
    middleware._is_global = True

    return middleware