from typing import Coroutine, Callable
import inspect

from .errors import RegistrationError

__all__ = (
    'Route',
    'PartialRoute',
    'WebsocketRoute',
    'Listener'
)

class PartialRoute:
    def __init__(self, path: str, method: str) -> None:
        self.path = path
        self.method = method

    def __repr__(self) -> str:
        return f'<PartialRoute path={self.path!r} method={self.method!r}>'

class Route:
    def __init__(self, path: str, method: str, callback, *, router) -> None:
        self._router = router

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

    def add_middleware(self, callback: Callable[..., Coroutine]):
        if not inspect.iscoroutinefunction(callback):
            raise RegistrationError('All middlewares must be async')

        self._middlewares.append(callback)
        return callback

    def middleware(self, callback):
        return self.add_middleware(callback)

    def after_request(self, callback):
        self._after_request = callback
        return callback

    def destroy(self):
        self._router.remove_route(self)
        return self

    def __repr__(self) -> str:
        return '<Route path={0.path!r} method={0.method!r}>'.format(self)

    async def __call__(self, *args, **kwargs):
        return await self.callback(*args, **kwargs)

class WebsocketRoute(Route):
    pass

class Listener:
    def __init__(self, callback, name) -> None:
        self.event = name
        self.callback = callback

    async def __call__(self, *args, **kwargs):
        return await self.callback(*args, **kwargs)
