from __future__ import annotations
from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from .request import Request

class CookieSession(Dict[str, Any]):
    cache: Dict[str, CookieSession] = {}

    @classmethod
    def create(cls, session_id: str) -> CookieSession:
        self = cls.cache.setdefault(session_id, CookieSession(session_id))
        return self

    @classmethod
    def from_request(cls, request: Request):
        cookie = request.app.settings['SESSION_COOKIE_NAME']
        session_id = request.cookies.get(str(cookie))

        if not session_id:
            return cls(None)

        return cls.create(session_id)

    def __init__(self, session_id: Optional[str]) -> None:
        self.id = session_id

        super().__init__()
