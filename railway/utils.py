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

import json
import warnings
import functools
import socket
import asyncio
from typing import TYPE_CHECKING, Any, Callable, Iterator, List, Optional, Type, Tuple, Union

from ._types import MaybeCoroFunc

if TYPE_CHECKING:
    from .response import Response

__all__ = (
    'copy_docstring',
    'clear_docstring',
    'maybe_coroutine',
    'LOCALHOST',
    'LOCALHOST_V6',
    'has_ipv6',
    'has_dualstack_ipv6',
    'is_ipv6',
    'is_ipv4',
    'validate_ip',
    'jsonify',
    'SETTING_ENV_PREFIX',
    'VALID_METHODS',
)

LOCALHOST = '127.0.0.1'
LOCALHOST_V6 = '::1'

def get_union_args(arg: Any) -> Tuple[Type]:
    """
    Gets the union types of a given argument. If the argument isn't an union, it returns a single element tuple.

    Parameters
    ----------
    arg: Any
        The argument to get the union types of.
    """
    origin = getattr(arg, '__origin__', None)

    if origin is Union:
        args = getattr(arg, '__args__')
        return args

    elif origin is not None:
        return (origin,)

    return (arg,)

def get_charset(content_type: str) -> Optional[str]:
    """
    Gets the charset from a content type header.

    Parameters
    ----------
    content_type: :class:`str`
        The content type header to get the charset from.

    Returns
    -------
    Optional[:class:`str`]
        The charset, or ``None`` if none was found.
    """
    split = content_type.split('; ')
    if len(split) > 1:
        _, charset = split[1]
        return charset.split('=')[1]

    return None


def copy_docstring(other: Callable[..., Any]) -> Callable[..., Callable[..., Any]]:
    """
    A decorator that copies the docstring of another function.

    Parameters
    ----------
    other: Callable[..., Any]
        The function to copy the docstring from.
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        func.__doc__ = other.__doc__
        return func
    return decorator

def clear_docstring(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    A decorator that clears the docstring of the decorated function.

    Parameters
    ----------
    func: Callable[..., Any]
        The function to clear the docstring of.
    """
    func.__doc__ = ''
    return func

async def maybe_coroutine(func: MaybeCoroFunc[Any], *args: Any, **kwargs: Any) -> Any:
    """
    Runs a function or coroutine, and returns its result,

    Parameters
    ----------
    func: Union[Callable[..., Coroutine], Callable[..., Any]]
        The function or coroutine to run.
    *args: Any
        Positional arguments to pass to the function or coroutine.
    **kwargs: Any
        Keyword arguments to pass to the function or coroutine.
    """
    if asyncio.iscoroutinefunction(func):
        return await func(*args, **kwargs)

    return func(*args, **kwargs)

def has_ipv6() -> bool:
    """
    A helper function that checks if the system supports IPv6.
    """
    return socket.has_ipv6

def has_dualstack_ipv6() -> bool:
    """
    A helper function that checks if the system has dual-stack IPv6 support
    """
    return socket.has_dualstack_ipv6()

def is_ipv6(ip: str) -> bool:
    """
    A helper function that checks if a given IP address is a valid IPv6 one.
    
    Parameters
    ----------
    ip: :class:`str`
        A string representing an IP address.
    """
    try:
        socket.inet_pton(socket.AF_INET6, ip)
        return True
    except socket.error:
        return False

def is_ipv4(ip: str) -> bool:
    """
    A helper function that checks if a given IP address is a valid IPv6 one.
    
    Parameters
    ----------
    ip: :class:`str`
        A string representing an IP address.
    """
    try:
        socket.inet_aton(ip)
        return True
    except socket.error:
        return False

def validate_ip(ip: str=None, *, ipv6: bool=False) -> str:
    """
    A helper function that validates an IP address.
    If an IP address is not given it will return the localhost address.

    Parameters
    ----------
    ip: Optional[:class:`str`]
        The IP address to validate.
    ipv6: Optional[:class:`bool`]
        Whether to validate an IPv6 address or not. Defaults to `False`.

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

def warn(message: str, category: Type[Warning], stacklevel: int=4):
    warnings.simplefilter('always', category)
    warnings.warn(message, category, stacklevel)

    warnings.simplefilter('default', category)

def deprecated(other: Optional[str]=None):
    def decorator(func: Callable[..., Any]):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if other:
                warning = f'{func.__name__} is deprecated, use {other} instead.'
            else:
                warning = f'{func.__name__} is deprecated.'

            warn(warning, DeprecationWarning)
            return func(*args, **kwargs)
        return wrapper
    return decorator

def jsonify(**kwargs: Any) -> 'Response':
    """
    Kinda like :func:`flask.jsonify`.

    Parameters
    ----------
    **kwargs: 
        Keyword arguments to pass to :func:`json.dumps`.

    Returns
    -------
    :class:`~.Response`
        A response object with the JSON data.
    """
    from .response import Response
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