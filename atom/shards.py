import typing
import inspect
import warnings
import yarl

from .errors import RouteRegistrationError, WebsocketRouteRegistrationError
from .objects import Route, WebsocketRoute
from .base import Base

if typing.TYPE_CHECKING:
    from .app import Application
    from .restful import RESTApplication

__all__ = (
    'Shard'
)

class Shard(Base):
    def __init__(self, name: str, *, url_prefix: str='', app: typing.Union['Application', 'RESTApplication']=None) -> None:
        super().__init__(url_prefix=url_prefix)

        self.name = name
        self.routes = []

        if app:
            self.app = app

            self._inject(self.app)
            self.app.shards[self.name] = self

    def get_routes(self):
        for route in self.routes:
            yield route

    def websocket(self, 
                  path: str, 
                  method: str, 
                  *, 
                  subprotocols=None):
        def decorator(coro):
            route = WebsocketRoute(path, method, coro)
            route.subprotocols = subprotocols

            return self.add_route(route, websocket=True)
        return decorator

    def add_route(self, route: typing.Union[Route, WebsocketRoute], *, websocket: bool=False):
        if not websocket:
            if not isinstance(route, Route):
                raise RouteRegistrationError('Expected Route but got {0!r} instead.'.format(route.__class__.__name__))

        if not inspect.iscoroutinefunction(route.coro):
            raise RouteRegistrationError('Routes must be async.')

        if route in self.routes:
            raise RouteRegistrationError('{0!r} is already a route.'.format(route.path))

        if websocket:
            if not isinstance(route, WebsocketRoute):
                fmt = 'Expected WebsocketRoute but got {0!r} instead'
                raise WebsocketRouteRegistrationError(fmt.format(route.__class__.__name__))

            self.routes.append(route)
            return route

        self.routes.append(route)
        return route

    def get(self, 
            path: typing.Union[str, yarl.URL], 
            *, 
            websocket: bool=False, 
            websocket_subprotocols=None):
        def decorator(func):
            if websocket:
                return self.websocket(path, 'GET', websocket_subprotocols)

            return self.route(path, 'GET')(func)
        return decorator

    def put(self, 
            path: typing.Union[str, yarl.URL], 
            *, 
            websocket: bool=False, 
            websocket_subprotocols=None):
        def decorator(func):
            if websocket:
                return self.websocket(path, 'PUT', websocket_subprotocols)

            return self.route(path, 'PUT')(func)
        return decorator

    def post(self, 
            path: typing.Union[str, yarl.URL], 
            *, 
            websocket: bool=False, 
            websocket_subprotocols=None):
        def decorator(func):
            if websocket:
                return self.websocket(path, 'POST', websocket_subprotocols)

            return self.route(path, 'POST')(func)
        return decorator

    def delete(self, 
            path: typing.Union[str, yarl.URL], 
            *, 
            websocket: bool=False, 
            websocket_subprotocols=None):
        def decorator(func):
            if websocket:
                return self.websocket(path, 'DELETE', websocket_subprotocols)

            return self.route(path, 'DELETE')(func)
        return decorator

    def head(self, 
            path: typing.Union[str, yarl.URL], 
            *, 
            websocket: bool=False, 
            websocket_subprotocols=None):
        def decorator(func):
            if websocket:
                return self.websocket(path, 'HEAD', websocket_subprotocols)

            return self.route(path, 'HEAD')(func)
        return decorator

    def options(self, 
                path: typing.Union[str, yarl.URL], 
                *, 
                websocket: bool=False, 
                websocket_subprotocols=None):
        def decorator(func):
            if websocket:
                return self.websocket(path, 'OPTIONS', websocket_subprotocols)

            return self.route(path, 'OPTIONS')(func)
        return decorator

    def patch(self, 
            path: typing.Union[str, yarl.URL], 
            *, 
            websocket: bool=False, 
            websocket_subprotocols=None):
        def decorator(func):
            if websocket:
                return self.websocket(path, 'PATCH', websocket_subprotocols)

            return self.route(path, 'PATCH')(func)
        return decorator


    def _inject(self, app):
        for middleware in self.middlewares:
            app.add_middleware(middleware)

        for name, listener in self._listeners.items():
            app.add_listener(listener, name)

        for route in self.routes:
            if isinstance(route, WebsocketRoute):
                app.add_route(route, websocket=True)
            else:
                app.add_route(route)

        for task in self._tasks:
            app.add_task(task)

        return app
