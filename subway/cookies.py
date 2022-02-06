from __future__ import annotations
import datetime

from typing import Dict, List, Literal, Optional, NamedTuple

__all__ = (
    'Cookie',
    'CookieJar'
)

class Cookie(NamedTuple):
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
    name: str
    value: str
    domain: Optional[str] = None
    http_only: bool = False
    secure: bool = False
    expires: Optional[datetime.datetime] = None
    path: Optional[str] = None
    same_site: Optional[Literal['Strict', 'Lax', 'None']] = None

    def to_string(self):
        base = 'Set-Cookie: {0.name}={0.value}'.format(self)
        if self.domain:
            base += '; Domain={0.domain}'.format(self)
        if self.http_only:
            base += '; HttpOnly'
        if self.secure:
            base += '; Secure'
        if self.expires:
            formatted = self.expires.strftime('%a, %d %b %Y %H:%M:%S GMT')
            base += '; Expires={0}'.format(formatted)
        if self.path:
            base += '; Path={0.path}'.format(self)
        if self.same_site:
            base += '; SameSite={0.same_site}'.format(self)

        return base

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
        secure: bool = False,
        expires: Optional[datetime.datetime] = None,
        path: Optional[str] = None,
        same_site: Optional[Literal['Strict', 'Lax', 'None']] = None
    ) -> Cookie:
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
        secure: :class:`bool`
            Whether the cookie is secure
        """
        cookie = Cookie(
            name=name, 
            value=value, 
            domain=domain,
            http_only=http_only,
            secure=secure,
            expires=expires,
            path=path,
            same_site=same_site
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
        return '; '.join(cookie.to_string() for cookie in self._cookies.values())

    def __iter__(self):
        return self._cookies.items().__iter__()

    def __bool__(self):
        return bool(self._cookies)

    def __len__(self):
        return len(self._cookies)

    def __str__(self) -> str:
        return self.encode()
