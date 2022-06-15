from __future__ import annotations

from typing import TYPE_CHECKING, List, Set, Tuple, Dict, Any, Type, Optional

from .types import CoroFunc
from .objects import Route
from .router import Router
from .request import Request
from .utils import VALID_METHODS, iscoroutinefunction
from .websockets import WebSocket, Data

if TYPE_CHECKING:
    from .app import Application

__all__ = (
    'ViewMeta',
    'HTTPView',
    'WebSocketHTTPView',
)

class PathMeta(type):
    def __new__(cls, name: str, bases: Tuple[Type[Any]], attrs: Dict[str, Any], **kwargs: Any):
        path = kwargs.get('path', '')
        attrs['__url_path__'] = path

        return super().__new__(cls, name, bases, attrs)

class ViewRoute(Route):
    def __init__(
        self, 
        view: HTTPView, 
        callback: CoroFunc[Any], 
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

class ViewMeta(PathMeta):
    """
    The meta class used for views.
    """
    def __new__(cls, name: str, bases: Tuple[Type[Any]], attrs: Dict[str, Any], **kwargs: Any):
        routes: List[CoroFunc[Any]] = []

        for key, value in attrs.items():
            if iscoroutinefunction(value) and key.upper() in VALID_METHODS:
                routes.append(value)

        attrs['__routes__'] = routes
        return super().__new__(cls, name, bases, attrs, **kwargs)

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

    def init(self, router: Router) -> None:
        """
        A helper method for adding routes to a router.

        Parameters
        ----------
        router: :class:`~.Router`
            The router to add the routes to.
        remove_routes: :class:`bool`
            Whether to remove the routes from the router.
        """
        for route in self.routes:
            route.router = router
            router.add_route(route)

    def destroy(self, router: Router):
        """
        A helper method for removing routes from a router.

        Parameters
        ----------
        router: :class:`~.Router`
            The router to remove the routes from.
        """
        for route in self.routes:
            router.remove_route(route)

        return self

class WebSocketHTTPView(metaclass=PathMeta):
    __url_path__: str

    def __init__(self, path: Optional[str] = None) -> None:
        if not path and not self.path:
            raise ValueError('A path must be specified.')

        self.path = path or self.path

    @property
    def path(self) -> str:
        return self.__url_path__

    @path.setter
    def path(self, value: str) -> None:
        self.__url_path__ = value

    async def on_receive(self, websocket: WebSocket, data: Data) -> Any:
        return

    async def on_connect(self, websocket: WebSocket, request: Request[Application]) -> bool:
        return True

    async def on_disconnect(self, websocket: WebSocket) -> None:
        return

    async def _listener(self, request: Request[Application], websocket: WebSocket) -> None:
        if not await self.on_connect(websocket, request):
            if not websocket.is_closed():
                return await websocket.close()

            return

        async with websocket:
            async for message in websocket:
                await self.on_receive(websocket, message)

        await self.on_disconnect(websocket)
