import json
import warnings
import functools
import socket
import asyncio
import weakref
from typing import Any, Callable, Iterator, List, Optional, Type, Tuple

from .response import Response
from ._types import MaybeCoroFunc

__all__ = (
    'AsyncResource',
    'maybe_coroutine',
    'LOCALHOST',
    'LOCALHOST_V6',
    'has_ipv6',
    'has_dualstack_ipv6',
    'is_ipv6',
    'is_ipv4',
    'validate_ip',
    'jsonify',
    'deprecated',
    'Deprecated',
    'SETTING_ENV_PREFIX',
    'VALID_METHODS'
)

LOCALHOST = '127.0.0.1'
LOCALHOST_V6 = '::1'

class AsyncResource:
    async def close(self):
        raise NotImplementedError

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()

async def maybe_coroutine(func: MaybeCoroFunc[Any], *args: Any, **kwargs: Any) -> Any:
    if asyncio.iscoroutinefunction(func):
        return await func(*args, **kwargs)

    return func(*args, **kwargs)

def has_ipv6() -> bool:
    """
    Returns: 
        True if the system can bind an IPv6 address.
    """
    return socket.has_ipv6

def has_dualstack_ipv6() -> bool:
    """
    Returns:
        True if the system has dualstack IPv6 support.
    """
    return socket.has_dualstack_ipv6()

def is_ipv6(ip: str) -> bool:
    """
    Args:
        ip: A string representing an address.
    
    Returns:
        True if the given IP is an IPv6 address.
    """
    try:
        socket.inet_pton(socket.AF_INET6, ip)
        return True
    except socket.error:
        return False

def is_ipv4(ip: str) -> bool:
    """
    Args:
        ip: A string representing an address.

    Returns:
        True if the given IP is an IPv4 address.
    """
    try:
        socket.inet_aton(ip)
        return True
    except socket.error:
        return False

def validate_ip(ip: str=None, *, ipv6: bool=False) -> str:
    """
    Validates an IP address

    Args:
        ip: The IP address to validate.
        ipv6: If True, validates an IPv6 address.

    Returns:
        The validated IP address.
    """
    if not ip:
        if ipv6:
            return LOCALHOST_V6

        return LOCALHOST

    if ipv6:
        if not is_ipv6(ip):
            ret = f'{ip!r} is not a valid IPv6 address'
            raise ValueError(ret)

        return ip
    else:
        if not is_ipv4(ip):
            ret = f'{ip!r} is not a valid IPv4 address'
            raise ValueError(ret)

        return ip

class Deprecated:
    def __init__(self, func: Callable[..., Any]) -> None:
        self.__repr = '<Deprecated name={0.__name__!r}>'.format(func)

    def __bool__(self):
        return False

    def __repr__(self) -> str:
        return self.__repr


SETTING_ENV_PREFIX = 'railway_'

VALID_METHODS = (
    "GET",
    "POST",
    "PUT",
    "HEAD",
    "OPTIONS",
    "PATCH",
    "DELETE"
)

def warn(message: str, category: Type[Warning]):
    warnings.simplefilter('always', category)
    warnings.warn(message, category, stacklevel=4)

    warnings.simplefilter('default', category)

def deprecated(other: Optional[str]=None):
    def decorator(func: Callable[..., Any]):
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Deprecated:
            if other:
                warning = f'{func.__name__} is deprecated, use {other} instead.'
            else:
                warning = f'{func.__name__} is deprecated.'

            warn(warning, DeprecationWarning)
            return Deprecated(func)
        return wrapper
    return decorator

def jsonify(**kwargs: Any) -> Response:
    """
    Kinda like `flask.jsonify`.

    Args:
        **kwargs: Keyword arguments to pass to `json.dumps`.

    Returns:
        A Response object.
    """
    data = json.dumps(kwargs, indent=4)

    resp = Response(data, content_type='application/json')
    return resp

def iter_headers(headers: bytes) -> Iterator[List[Any]]:
    offset = 0

    while True:
        index = headers.index(b'\r\n', offset) + 2
        data = headers[offset:index]
        offset = index

        if data == b'\r\n':
            break

        yield [item.strip().decode() for item in data.split(b':', 1)]

def find_headers(data: bytes) -> Tuple[Iterator[List[Any]], bytes]:
    while True:
        end = data.find(b'\r\n\r\n') + 4

        if end != -1:
            headers = data[:end]
            body = data[end:]

            return iter_headers(headers), body