from __future__ import annotations
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .sessions import HTTPSession
    from .abc import Hooker

class InvalidHost(TypeError):
    def __init__(self, host: Optional[str]) -> None:
        message = f'{host!r} is an invalid host'
        super().__init__(message)

class HookerError(Exception):
    def __init__(self, message: Optional[str]=None, *, hooker: Hooker, client: HTTPSession) -> None:
        self.hooker = hooker
        self.client = client

        super().__init__('' if message is None else message)

class HookerAlreadyConnected(HookerError):
    pass

class HookerClosed(HookerError):
    pass

class HandshakeError(HookerError):
    pass