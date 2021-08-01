from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .request import Request

class CookieSession(dict):
    __sessions__ = {}

    @classmethod
    def from_request(cls, request: Request) -> 'CookieSession':
        cookie = request.app.settings['SESSION_COOKIE_NAME']
        session_id = request.cookies.get(cookie)

        if not session_id:
            return cls(None)

        self = cls.__sessions__.get(session_id)
        if not self:
            self = cls(session_id)
            self.__sessions__[session_id] = self

        return self

    def __init__(self, session_id: str) -> None:
        self.id: str = session_id

        super().__init__()