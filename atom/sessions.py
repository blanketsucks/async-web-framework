from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .request import Request

class CookieSession(dict):
    cache = {}

    @classmethod
    def create(cls, session_id: str) -> CookieSession:
        self = cls.cache.setdefault(session_id, CookieSession(session_id))
        return self

    @classmethod
    def from_request(cls, request: Request) -> 'CookieSession':
        cookie = request.app.settings['SESSION_COOKIE_NAME']
        session_id = request.cookies.get(cookie)

        if not session_id:
            return cls(None)

        return cls.create(session_id)

    def __init__(self, session_id: str) -> None:
        self.id: str = session_id

        super().__init__()
