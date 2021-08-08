from __future__ import annotations
from typing import Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .request import Request

class Cookie:
    def __init__(self, 
                name: str, 
                value: str, 
                domain: Optional[str], 
                http_only: bool,
                secure: bool):
        self.name = name
        self.value = value
        self.http_only = http_only
        self.secure = secure
        self._domain = domain

    def set_domain(self, domain: str):
        self._domain = domain

    def __str__(self):
        return f'Set-Cookie: {self.name}={self.value};'

    def __repr__(self) -> str:
        return '<Cookie name={0.name!r} value={0.value!r}>'.format(self)
    
    
class CookieJar:
    def __init__(self):
        self._cookies: Dict[str, Cookie] = {}

    @classmethod
    def from_request(cls, request: Request) -> CookieJar:
        header = request.headers.get('Cookie', '')
        if not header:
            return cls()

        cookies = header.split('; ')

        jar = cls()
        for cookie in cookies:
            name, value = cookie.split('=', 1)
            jar.add_cookie(name, value)

        return jar

    def add_cookie(self, name: str, value: str, *, domain: str=None, http_only: bool=False, is_secure: bool=False):
        cookie = Cookie(
            name=name, 
            value=value, 
            domain=domain,
            http_only=http_only,
            secure=is_secure
        )
        self._cookies[name] = cookie

        return cookie

    def get_cookie(self, name: str) -> Cookie:
        return self._cookies.get(name)

    def encode(self):
        encoded = []
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