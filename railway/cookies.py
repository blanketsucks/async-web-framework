from __future__ import annotations
from typing import Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .request import Request

class Cookie:
    """
    Attributes:
        name: The name of the cookie.
        value: The value of the cookie.
        http_only: Whether the cookie is http only.
        secure: Whether the cookie is marked as secure.
    """
    def __init__(self, 
                name: str, 
                value: str, 
                domain: Optional[str], 
                http_only: bool,
                secure: bool):
        self.name: str = name
        self.value: str = value
        self.http_only: bool = http_only
        self.secure: bool = secure
        self._domain = domain

    def set_domain(self, domain: str) -> None:
        """
        Sets the cookie's domain

        Args:
            domain: The domain to set the cookie to.
        """
        self._domain = domain

    def __str__(self):
        return f'Set-Cookie: {self.name}={self.value};'

    def __repr__(self) -> str:
        return '<Cookie name={0.name!r} value={0.value!r}>'.format(self)
    
    
class CookieJar:
    """
    A cookie jar used to store cookies.
    """
    def __init__(self):
        self._cookies: Dict[str, Cookie] = {}

    @classmethod
    def from_request(cls, request: Request) -> CookieJar:
        """
        Builds a cookie jar from a request.

        Args:
            request: The request to build the cookie jar from.

        Returns:
            A cookie jar containing the cookies from the request.
        """
        header = request.headers.get('Cookie', '')
        if not header:
            return cls()

        cookies = header.split('; ')

        jar = cls()
        for cookie in cookies:
            name, value = cookie.split('=', 1)
            jar.add_cookie(name, value)

        return jar

    def add_cookie(self, name: str, value: str, *, domain: Optional[str]=None, http_only: bool=False, is_secure: bool=False):
        """
        Adds a cookie to the jar

        Args:
            name: The name of the cookie
            value: The value of the cookie
            domain: The domain of the cookie
            http_only: Whether the cookie is http only
            is_secure: Whether the cookie is secure
        """
        cookie = Cookie(
            name=name, 
            value=value, 
            domain=domain,
            http_only=http_only,
            secure=is_secure
        )
        self._cookies[name] = cookie

        return cookie

    def get_cookie(self, name: str) -> Optional[Cookie]:
        """
        Gets a cookie from the jar.

        Args:
            name: The name of the cookie to get.
        """
        return self._cookies.get(name)

    def encode(self):
        """
        Encodes the cookie jar as a string.
        """
        encoded: List[str] = []

        for cookie in self._cookies.values():
            encoded.append(str(cookie))

        return '; '.join(encoded)

    def __iter__(self):
        return self._cookies.values().__iter__()

    def __bool__(self):
        return bool(self._cookies)

    def __len__(self):
        return len(self._cookies)

    def __str__(self) -> str:
        return self.encode()