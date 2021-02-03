import typing
import inspect

from .errors import RouteRegistrationError
from .objects import Route
from .base import AppBase

class Shard(AppBase):
    def __init__(self, *, url_prefix: str='') -> None:
        self.url_prefix = url_prefix

        self._routes = {}
        super().__init__(url_prefix=self.url_prefix)
    
    def add_route(self, route: Route):
        if not inspect.iscoroutinefunction(route.coro):
            raise RouteRegistrationError('Routes must be async.')

        if (route.method, route.path) in self._router.routes:
            raise RouteRegistrationError('{0!r} is already a route.'.format(route.path))

        self._routes[(route.path, route.method)] = route.coro
        return route
