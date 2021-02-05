import typing

__all__ = (
    'Route',
    'Middleware',
    'Listener'
)

class Route:
    def __init__(self, path: str, method: str, coro: typing.Coroutine) -> None:
        self._path = path
        self._method = method
        self._coro = coro

    @property
    def path(self):
        return self._path

    @property
    def method(self):
        return self._method

    @property
    def coro(self):
        return self._coro


class Middleware:
    def __init__(self, coro: typing.Coroutine) -> None:
        self._coro = coro

    @property
    def coro(self):
        return self._coro


class Listener:
    def __init__(self, coro: typing.Coroutine, name: str=None) -> None:
        self._event = name
        self._coro = coro

    @property
    def event(self):
        return self._event

    @property
    def coro(self):
        return self._coro
