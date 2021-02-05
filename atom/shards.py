import typing
import inspect

from .errors import RouteRegistrationError
from .objects import Route
from .base import AppBase

class Shard(AppBase):
    def __init__(self, name: str, *, url_prefix: str='') -> None:
        self.url_prefix = url_prefix
        self.name = name

        self._routes = {}
        super().__init__(url_prefix=self.url_prefix)

    @property
    def routes(self):
        return self._routes
    
    def add_route(self, route: Route):
        if not inspect.iscoroutinefunction(route.coro):
            raise RouteRegistrationError('Routes must be async.')

        if (route.method, route.path) in self._routes:
            raise RouteRegistrationError('{0!r} is already a route.'.format(route.path))

        self._routes[(route.path, route.method)] = route.coro
        return route

    def _inject(self, app):
        for middleware in self._middlewares:
            app.add_middleware(middleware)

        for name, listener in self._listeners.items():
            app.add_listener(listener, name)

        for (path, method), coro in self._routes.items():
            route = Route(path, method, coro)
            app.add_route(route)

        for task in self._tasks:
            app.add_task(task)

        return app
