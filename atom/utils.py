import json
import warnings
import functools
from typing import Any, Callable, Iterator, List, Optional, Type, Tuple

from .response import  Response

__all__ = (
    'jsonify',
    'deprecated',
    'Deprecated',
    'SETTING_ENV_PREFIX',
    'VALID_METHODS'
)

class Deprecated:
    def __init__(self, func: Callable[..., Any]) -> None:
        self.__repr = '<Deprecated name={0.__name__!r}>'.format(func)

    def __bool__(self):
        return False

    def __repr__(self) -> str:
        return self.__repr


SETTING_ENV_PREFIX = 'ATOM_'

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
        def wrapper(*args: Any, **kwargs: Any) -> Deprecated:
            if other:
                warning = f'{func.__name__} is deprecated, use {other} instead.'
            else:
                warning = f'{func.__name__} is deprecated.'

            warn(warning, DeprecationWarning)
            return Deprecated(func)
        return wrapper
    return decorator



def jsonify(*, response: bool=True, **kwargs: Any):
    """Inspired by Flask's jsonify"""
    data = json.dumps(kwargs, indent=4)

    if response:
        resp = Response(data, content_type='application/json')
        return resp

    return data

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