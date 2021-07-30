from __future__ import annotations
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from .request import Request

class CookieSession:
    __sessions__ = {}

    def __init__(self) -> None:
        pass