from __future__ import annotations

from typing import Dict, List, Optional

__all__ = (
    'Cookie',
    'CookieJar'
)

class Cookie:
    """
    Parameters
    ----------
    name: :class:`str`
        The name of the cookie.
    value: :class:`str`
        The value of the cookie.
    domain: Optional[:class:`str`]
        The domain of the cookie.
    http_only: :class:`bool`
        Whether the cookie is http only.
    secure: :class:`bool`
        Whether the cookie is marked as secure.

    Attributes
    ----------
    name: :class:`str`
        The name of the cookie.
    value: :class:`str`
        The value of the cookie.
    http_only: :class:`bool`
        Whether the cookie is http only.
    secure: :class:`bool`
        Whether the cookie is marked as secure.
    """
    def __init__(
        self,
        name: str,
        value: str,
        domain: Optional[str],
        http_only: bool,
        secure: bool
    ):
        self.name: str = name
        self.value: str = value
        self.http_only: bool = http_only
        self.secure: bool = secure
        self._domain = domain

    def set_domain(self, domain: str) -> None:
        """
        Sets the cookie's domain

        Parameters
        ----------
        domain: :class:`str`
            The domain to set the cookie to.
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
    def from_headers(cls, headers: Dict[str, str]) -> CookieJar:
        """
        Builds a cookie jar from a request.

        Parameters
        ----------
        headers: :class:`dict`
            The headers to parse the cookie jar from.
        """
        header = headers.get('Cookie')
        if not header:
            return cls()

        cookies = header.split('; ')

        jar = cls()
        for cookie in cookies:
            name, value = cookie.split('=', 1)
            jar.add_cookie(name, value)

        return jar

    def add_cookie(
        self,
        name: str,
        value: str,
        *,
        domain: Optional[str] = None,
        http_only: bool = False,
        is_secure: bool = False
    ):
        """
        Adds a cookie to the jar

        Parameters
        ----------
        name: :class:`str`
            The name of the cookie
        value: :class:`str`
            The value of the cookie
        domain: Optional[:class:`str`]
            The domain of the cookie
        http_only: :class:`bool`
            Whether the cookie is http only
        is_secure: :class:`bool`
            Whether the cookie is secure
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

    def update(self, cookies: Dict[str, Cookie]) -> None:
        return self._cookies.update(cookies)

    def get_cookie(self, name: str) -> Optional[Cookie]:
        """
        Gets a cookie from the jar.

        Parameters
        ----------
        name: :class:`str`
            The name of the cookie to get.
        """
        return self._cookies.get(name)

    def get(self, name: str) -> Optional[Cookie]:
        """
        Equivalent to :meth:`~.get_cookie`

        Parameters
        ----------
        name: :class:`str`
            The name of the cookie to get.
        """
        return self._cookies.get(name)

    def encode(self):
        """
        Encodes the cookie jar as string.
        """
        encoded: List[str] = []

        for cookie in self._cookies.values():
            encoded.append(str(cookie))

        return '; '.join(encoded)

    def __iter__(self):
        return self._cookies.items().__iter__()

    def __bool__(self):
        return bool(self._cookies)

    def __len__(self):
        return len(self._cookies)

    def __str__(self) -> str:
        return self.encode()
