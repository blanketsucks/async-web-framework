from __future__ import annotations
from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from .request import Request

class CookieSession(Dict[str, Any]):
    """
    A session that is managed by a cookie.
    
    """
    cache: Dict[str, CookieSession] = {}

    @classmethod
    def create(cls, session_id: str) -> CookieSession:
        """
        Creates a new session with the given ID.
        If a session with the given ID already exists, it is returned instead.

        Args:
            session_id: The ID of the session. (meaning the value of the cookie used)

        Returns:

        
        """
        self = cls.cache.setdefault(session_id, CookieSession(session_id))
        return self

    @classmethod
    def from_request(cls, request: Request) -> CookieSession:
        """
        Returns a session from the given request.

        Args:
            request: The request to get the session from.

        Returns:
            The session from the request.
        """
        cookie = request.app.settings['session_cookie_name']
        session_id = request.cookies.get(str(cookie))

        if not session_id:
            return cls(None)

        return cls.create(session_id)

    def __init__(self, session_id: Optional[str]) -> None:
        self.id = session_id

        super().__init__()
