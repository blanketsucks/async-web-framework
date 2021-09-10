"""
MIT License

Copyright (c) 2021 blanketsucks

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
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

        Parameters:
            session_id: The ID of the session. (meaning the value of the cookie used)

        Returns:

        
        """
        self = cls.cache.setdefault(session_id, CookieSession(session_id))
        return self

    @classmethod
    def from_request(cls, request: Request) -> CookieSession:
        """
        Returns a session from the given request.

        Parameters:
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
