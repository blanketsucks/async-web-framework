from typing import Any, Dict, List, Tuple, Type
import functools
import inspect

from ._types import CoroFunc

from .objects import Route
from .router import Router
from .utils import VALID_METHODS

__all__ = (
    'HTTPView',
    'ViewMeta'
)

class ViewMeta(type):
    __url_route__: str
    __routes__: List[CoroFunc]

    def __new__(cls, name: str, bases: Tuple[Type[Any]], attrs: Dict[str, Any], **kwargs: Any):
        attrs['__url_route__'] = kwargs.get('path', '')

        self = super().__new__(cls, name, bases, attrs)
        view_routes: List[CoroFunc] = []

        for base in self.mro():
            for _, value in base.__dict__.items():
                if inspect.iscoroutinefunction(value):
                    if value.__name__.upper() in VALID_METHODS:
                        view_routes.append(value)

        self.__routes__ = view_routes
        return self

class HTTPView(metaclass=ViewMeta):
    __url_route__: str
    __routes__: List[CoroFunc]

    def add_route(self, method: str, coro: CoroFunc):
        setattr(self, method, coro)
        return coro

    def as_routes(self, router: Router):
        routes: List[Route] = []

        for coro in self.__routes__:
            actual = functools.partial(coro, self)

            route = Route(self.__url_route__, coro.__name__.upper(), actual, router=router)
            router.add_route(route)

            routes.append(route)
            
        return routes
