import typing
import functools

from .request import Request
from .meta import ViewMeta
from .objects import Route, WebsocketRoute

__all__ = (
    'HTTPView',
    'WebsocketHTTPView'
)


class HTTPView(metaclass=ViewMeta):
    async def dispatch(self, request: Request, *args, **kwargs):
        coro = getattr(self, request.method.lower(), None)

        if coro:
            await coro(*args, **kwargs)

    def add(self, method: str, coro: typing.Callable):
        setattr(self, method, coro)
        return coro

    def as_routes(self):
        routes = []

        for coro in self.__routes__:
            actual = functools.partial(coro, self)

            route = Route(self.__url_route__, coro.__name__.upper(), actual)
            routes.append(route)

        yield from routes


class WebsocketHTTPView(HTTPView):
    def as_routes(self):
        routes = []

        for coro in self.__routes__:
            actual = functools.partial(coro, self)

            route = WebsocketRoute(self.__url_route__, coro.__name__.upper(), actual)
            routes.append(route)

        yield from routes
