import typing
import inspect

from .errors import MiddlewareRegistrationError

__all__ = (
    'Route',
    'WebsocketRoute',
    'Middleware',
    'Listener'
)

class Route:
    def __init__(self, path, method, callback, *, app) -> None:
        self._app = app

        self.path = path
        self.method = method
        self.callback = callback

        self._middlewares = []
        self._after_request =None

    @property
    def middlewares(self):
        return self._middlewares

    def cleanup_middlewares(self):
        self._middlewares.clear()

    def add_middleware(self, callback: typing.Callable[..., typing.Coroutine]):
        if not inspect.iscoroutinefunction(callback):
            raise MiddlewareRegistrationError('All middlewares must be async')

        self._middlewares.append(callback)
        return Middleware(callback, self)

    def middleware(self, callback):
        return self.add_middleware(callback)

    def after_request(self, callback):
        self._after_request = callback
        return callback

    def destroy(self):
        self._app.remove_route(self)
        return self

    def __repr__(self) -> str:
        return '<Route path={0.path!r} method={0.method!r}>'.format(self)

    async def __call__(self, *args, **kwargs):
        return await self.callback(*args, **kwargs)


class WebsocketRoute(Route):
    pass

class Middleware:
    def __init__(self, callback, route) -> None:
        self._route = route
        self.callback = callback

    @property
    def route(self):
        return self._route

    async def __call__(self, *args, **kwargs):
        return await self.callback(*args, **kwargs)


class Listener:
    def __init__(self, callback, name) -> None:
        self.event = name
        self.callback = callback

    async def __call__(self, *args, **kwargs):
        return await self.callback(*args, **kwargs)
