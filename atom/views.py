from typing import List
import functools

from ._types import CoroFunc
from .meta import ViewMeta
from .objects import Route
from .router import Router
__all__ = (
    'HTTPView',
)

class HTTPView(metaclass=ViewMeta):
    __url_route__: str
    __routes__: List[CoroFunc]

    def add_route(self, method: str, coro: CoroFunc):
        setattr(self, method, coro)
        return coro

    def as_routes(self, router: Router, *, remove_routes: bool=False):
        routes: List[Route] = []

        for coro in self.__routes__:
            actual = functools.partial(coro, self)

            route = Route(self.__url_route__, coro.__name__.upper(), actual, router=router)

            if remove_routes:
                router.remove_route(route)
            else:
                router.add_route(route)

            routes.append(route)
            
        return routes
