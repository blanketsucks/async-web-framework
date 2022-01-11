from typing import List, Tuple, Dict, Any, Type
import functools

from .types import CoroFunc
from .objects import Route
from .router import Router
from .utils import VALID_METHODS, iscoroutinefunction

__all__ = (
    'ViewMeta',
    'HTTPView',
)


class ViewMeta(type):
    """
    The meta class used for views.
    """
    __routes__: List[CoroFunc]

    def __new__(cls, name: str, bases: Tuple[Type[Any]], attrs: Dict[str, Any], **kwargs: Any):
        attrs['__url_route__'] = kwargs.get('path', '')
        attrs['__routes__'] = []

        self = super().__new__(cls, name, bases, attrs)
        view_routes: List[CoroFunc] = []

        for base in self.mro():
            for _, value in base.__dict__.items():
                if iscoroutinefunction(value):
                    if value.__name__.upper() in VALID_METHODS:
                        view_routes.append(value)

        self.__routes__ = view_routes
        return self


class HTTPView(metaclass=ViewMeta):
    """
    Examples
    --------

    .. code-block :: python3

        import railway

        app = railway.Application()

        class MyView(railway.HTTPView, path='/my-view'):

            async def get(self, request: railway.Request):
                return 'A creative response'

        app.add_view(MyView())

    """
    __url_route__: str
    __routes__: List[CoroFunc]

    @property
    def url_route(self) -> str:
        """
        The url route for this view.
        """
        return self.__url_route__

    def routes(self) -> List[CoroFunc]:
        """
        The routes for this view.
        """
        return self.__routes__

    def add_route(self, method: str, callback: CoroFunc) -> CoroFunc:
        """
        Adds a route to this view.

        Parameters
        ----------
        method: :class:`str`
            The HTTP method of the route.
        callback: Callable[..., Any]
            The callback to register the route with.
        """
        setattr(self, method, callback)
        return callback

    def as_routes(
        self, router: Router, *, remove_routes: bool = False
    ) -> List[Route]:
        """
        A helper method for adding routes to a router or removing them.

        Parameters
        ----------
        router: :class:`~.Router`
            The router to add the routes to.
        remove_routes: :class:`bool`
            Whether to remove the routes from the router.
        """
        routes: List[Route] = []

        for coro in self.routes():
            actual = functools.partial(coro, self)

            route = Route(self.__url_route__, coro.__name__.upper(), actual, router=router)

            if remove_routes:
                router.remove_route(route)
            else:
                router.add_route(route)

            routes.append(route)

        return routes
