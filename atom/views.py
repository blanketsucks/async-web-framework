import typing
from .request import Request

__all__ = (
    'ViewMeta',
    'HTTPView',
    'WebsocketHTTPView'
)

class ViewMeta(type):
    def __new__(cls, name, base, attrs, **kwargs):
        self = super().__new__(name, base, attrs)
        return self

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