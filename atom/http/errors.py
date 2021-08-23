from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .client import HTTPSession
    from .abc import Hooker

class InvalidHost(TypeError):
    def __init__(self, host: str) -> None:
        message = f'{host!r} is an invalid host'
        super().__init__(message)

class HookerError(Exception):
    def __init__(self, message: str=None, *, hooker: Hooker, client: HTTPSession) -> None:
        self.hooker = hooker
        self.client = client

        super().__init__('' if message is None else message)

class HookerAlreadyConnected(HookerError):
    pass

class HookerClosed(HookerError):
    pass

class HandshakeError(HookerError):
    pass