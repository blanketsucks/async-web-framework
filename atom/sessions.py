from __future__ import annotations
from typing import TYPE_CHECKING, Type, TypeVar

_T = TypeVar('_T')

if TYPE_CHECKING:
    from .request import Request

class CookieSession(dict):
    cache = {}

    @classmethod
    def create(cls: Type[_T], session_id: str) -> _T:
        self = cls.cache.setdefault(session_id, CookieSession(session_id))
        return self

    @classmethod
    def from_request(cls: Type[_T], request: Request) -> _T:
        cookie = request.app.settings['SESSION_COOKIE_NAME']
        session_id = request.cookies.get(cookie)

        if not session_id:
            return cls(None)

        return cls.create(session_id)

    def __init__(self, session_id: str) -> None:
        self.id: str = session_id

        super().__init__()
