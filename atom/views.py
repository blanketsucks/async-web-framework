import typing
from .request import Request
from .meta import ViewMeta

__all__ = (
    'HTTPView',
    'WebsocketHTTPView'
)

class HTTPView(metaclass=ViewMeta):
    async def dispatch(self, request: Request, *args, **kwargs):
        coro = getattr(self, request.method.lower(), None)

        if coro:
            await coro(*args, **kwargs)

    def add(self, method: str, coro: typing.Coroutine):
        setattr(self, method, coro)
        return coro

class WebsocketHTTPView(HTTPView):
    pass