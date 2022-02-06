from __future__ import annotations

from typing import List, Tuple, Dict, Any, Type, Optional
import functools

from .types import CoroFunc
from .objects import Route
from .router import Router
from .utils import VALID_METHODS, iscoroutinefunction

__all__ = (
    'ViewMeta',
    'HTTPView',
)

class ViewRoute(Route):
    def __init__(
        self, 
        view: HTTPView, 
        callback: CoroFunc, 
        *, 
        name: Optional[str] = None, 
        router: Optional[Router] = None
    ) -> None:
        self.view = view

        method = callback.__name__.upper()
        super().__init__(view.path, method, callback, name=name, router=router)

        self.parent = view

    def __call__(self, *args, **kwargs) -> Any:
        return super().__call__(*args, **kwargs)


class ViewMeta(type):
    """
    The meta class used for views.
    """
    def __new__(cls, name: str, bases: Tuple[Type[Any]], attrs: Dict[str, Any], **kwargs: Any):
        path = kwargs.get('path', '')
        routes: List[CoroFunc[Any]] = []

        for key, value in attrs.items():
            if iscoroutinefunction(value) and key.upper() in VALID_METHODS:
                routes.append(value)

        attrs['__url_path__'] = path
        attrs['__routes__'] = routes

        return super().__new__(cls, name, bases, attrs)

class HTTPView(metaclass=ViewMeta):
    """
    Examples
    --------

    .. code-block :: python3

        import subway

        app = subway.Application()

        class MyView(subway.HTTPView, path='/my-view'):

            async def get(self, request: subway.Request):
                return 'A creative response'

        app.add_view(MyView())

    """
    __url_path__: str
    __routes__: List[CoroFunc]

    @property
    def path(self) -> str:
        """
        The url route for this view.
        """
        return self.__url_path__

    @path.setter
    def path(self, value: str) -> None:
        self.__url_path__ = value

    @property
    def routes(self) -> List[ViewRoute]:
        """
        The routes for this view.
        """
        return [ViewRoute(self, callback) for callback in self.__routes__]

    def add_route(self, method: str, callback: CoroFunc[Any]) -> CoroFunc[Any]:
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

    def init(
        self, router: Router, *, remove_routes: bool = False
    ) -> None:
        """
        A helper method for adding routes to a router or removing them.

        Parameters
        ----------
        router: :class:`~.Router`
            The router to add the routes to.
        remove_routes: :class:`bool`
            Whether to remove the routes from the router.
        """
        for route in self.routes:
            route.router = router

            if remove_routes:
                router.remove_route(route)
            else:
                router.add_route(route)

            

