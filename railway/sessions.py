from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional
from abc import ABC, abstractclassmethod

if TYPE_CHECKING:
    from .app import Application
    from .request import Request

__all__ = 'AbstractSession', 'CookieSession',

class AbstractSession(ABC):
    
    @classmethod
    @abstractclassmethod
    async def from_request(cls, request: Request[Application]):
        raise NotImplementedError

class CookieSession(AbstractSession, Dict[str, Any]):
    """
    A session that is managed by a cookie.
    """
    cache: Dict[str, CookieSession] = {}

    @classmethod
    async def from_request(cls, request: Request[Application]) -> CookieSession:
        """
        Returns a session from the given request.

        Parameters
        ----------
        request: :class:`~railway.request.Request`
            The request to get the session from.
        """
        cookie = request.get_default_session_cookie()
        if not cookie:
            return cls(None)

        return cls.cache.setdefault(cookie.value, cls(cookie.value))

    def __init__(self, session_id: Optional[str]) -> None:
        self.id = session_id

        super().__init__()
