from __future__ import annotations
from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    from .client import HTTPSession
    from .websockets import WebsocketClient
    from .abc import Hooker

class InvalidHost(TypeError):
    def __init__(self, host: str) -> None:
        message = f'{host!r} is an invalid host'
        super().__init__(message)

class HookerError(Exception):
    def __init__(self, message: str, *, hooker: Hooker, client: Union[HTTPSession, WebsocketClient]) -> None:
        self.hooker = hooker
        self.client = client

        super().__init__(message)

class HookerAlreadyConnected(HookerError):
    pass

class HookerClosed(HookerError):
    pass

class HandshakeError(HookerError):
    pass