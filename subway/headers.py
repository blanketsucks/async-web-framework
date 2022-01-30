from typing import Dict, Optional
from functools import cached_property

from .cookies import CookieJar
from . import utils

__all__ = 'Headers',

class Headers(Dict[str, str]):
    
    @property
    def content_type(self) -> Optional[str]:
        return self.get('Content-Type')

    @property
    def content_length(self) -> Optional[int]:
        length = self.get('Content-Length')
        if length:
            return int(length)

        return None

    @property
    def charset(self) -> Optional[str]:
        content_type = self.content_type
        if content_type:
            return utils.get_charset(content_type)

        return None

    @property
    def user_agent(self) -> Optional[str]:
        return self.get('User-Agent')

    @cached_property
    def cookies(self) -> CookieJar:
        return CookieJar.from_headers(self)

    @property
    def host(self) -> Optional[str]:
        return self.get('Host')