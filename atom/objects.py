import typing

__all__ = (
    'Route',
    'WebsocketRoute',
    'Middleware',
    'Listener'
)

class Route:
    def __init__(self, path: str, method: str, coro: typing.Coroutine) -> None:
        self.path = path
        self.method = method
        self.coro = coro

    def __repr__(self) -> str:
        return '<Route path={0.path!r} method={0.method!r}>'.format(self)

    async def __call__(self, *args, **kwargs):
        return await self.coro(*args, **kwargs)

class WebsocketRoute:
    def __init__(self, path: str, method: str, coro: typing.Coroutine) -> None:
        self.path = path
        self.method = method
        self.coro = coro
        self.subprotocols = None

    def __repr__(self) -> str:
        return '<WebsocketRoute path={0.path!r} method={0.method!r}>'.format(self)

    async def __call__(self, *args, **kwargs):
        return await self.coro(*args, **kwargs)
        
class Middleware:
    def __init__(self, coro: typing.Coroutine) -> None:
        self.coro = coro

    async def __call__(self, *args, **kwargs):
        return await self.coro(*args, **kwargs)

class Listener:
    def __init__(self, coro: typing.Coroutine, name: str=None) -> None:
        self.event = name
        self.coro = coro

    async def __call__(self, *args, **kwargs):
        return await self.coro(*args, **kwargs)