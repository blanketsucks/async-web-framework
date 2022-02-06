from __future__ import annotations
from types import FrameType

from typing import TYPE_CHECKING, Any, Callable, Dict, Optional, Type, Tuple, Union, TypeVar, List, Iterator, overload, Literal
from pathlib import Path
import warnings
import functools
import json
import signal
import sys
import socket
import os
import asyncio
import inspect

try:
    import orjson
except ImportError:
    HAS_ORJSON = False
else:
    HAS_ORJSON = True

from .types import (
    MaybeCoroFunc, 
    StrPath, 
    StrURL, 
    JSONResponseBody, 
    Header, 
    ParsedResult, 
    StripedResult, 
    NonStripedResult
)
from .url import URL

if TYPE_CHECKING:
    from typing_extensions import ParamSpec

    T = TypeVar('T')
    _T = TypeVar('_T', str, bytes)

    P = ParamSpec('P')

__all__ = (
    'LOCALHOST',
    'LOCALHOST_V6',
    'GUID',
    'CLRF',
    'SETTING_ENV_PREFIX',
    'VALID_METHODS',
    'dumps',
    'loads',
    'add_signal_handler',
    'to_url',
    'socket_is_closed',
    'listdir',
    'clean_values',
    'unwrap_function',
    'iscoroutinefunction',
    'isasyncgenfunction',
    'copy_docstring',
    'clear_docstring',
    'maybe_coroutine',
    'has_ipv6',
    'has_dualstack_ipv6',
    'is_ipv6',
    'is_ipv4',
    'validate_ip',
    'jsonify',
    'get_charset',
    'get_union_args',
    'parse_headers',
    'parse_http_data',
    'deprecated',
)

LOCALHOST = '127.0.0.1'
LOCALHOST_V6 = '::1'
GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
CLRF = b'\r\n'
SETTING_ENV_PREFIX = 'subway_'
VALID_METHODS = (
    "GET",
    "POST",
    "PUT",
    "HEAD",
    "OPTIONS",
    "PATCH",
    "DELETE",
)

if HAS_ORJSON:
    def dumps(obj: Any, **kwargs: Any) -> str:
        data = orjson.dumps(obj, **kwargs)
        return data.decode('utf-8')

    def loads(obj: str, **kwargs: Any) -> Any:
        return orjson.loads(obj)
else:
    def dumps(obj: Any, **kwargs: Any) -> str:
        return json.dumps(obj, **kwargs)

    def loads(obj: str, **kwargs: Any) -> Any:
        return json.loads(obj, **kwargs)

def add_signal_handler(sig: int, handler: Callable[[signal.Signals, FrameType], Any], *args: Any, **kwargs: Any) -> None:
    """
    Adds a signal handler.

    Parameters
    ----------
    sig: :class:`int`
        The signal to handle.
    handler: Callable[[:class:`signal.Signals`, :class:`types.FrameType`], Any]
        The signal handler.
    *args: Any
        The arguments to pass to the signal handler.
    **kwargs: Any
        The keyword arguments to pass to the signal handler.
    """
    if sig not in signal.valid_signals():
        raise ValueError(f'{sig} is not a valid signal')

    def _handler(s: int, f: Any) -> Any:
        return handler(signal.Signals(s), f)

    partial = functools.partial(_handler, *args, **kwargs)
    signal.signal(sig, partial)

def to_url(url: StrURL) -> URL:
    """
    Converts a string to a :class:`~.URL` object.

    Parameters
    ----------
    url: :class:`str`
        The URL to convert.

    Returns
    -------
    :class:`~.URL`
        The converted URL.
    """
    return URL(url) if isinstance(url, str) else url

def socket_is_closed(sock: socket.socket) -> bool:
    """
    Checks if a socket is closed.

    Parameters
    ----------
    sock: :class:`socket.socket`
        The socket to check.
    """
    return sock.fileno() == -1

def listdir(path: Union[StrPath, Path], recursive: bool = False) -> Iterator[Path]:
    """
    Lists the contents of a directory.

    Parameters
    ----------
    path: Union[:class:`str`, :class:`pathlib.Path`]
        The path to list.
    recursive: :class:`bool`
        Whether to recursively list the contents of subdirectories.
    """
    if isinstance(path, (str, os.PathLike)):
        path = Path(path)

    for entry in path.iterdir():
        if entry.is_dir() and recursive:
            yield from listdir(entry, recursive)
        else:
            yield entry

def clean_values(values: List[_T]) -> List[_T]:
    """
    Cleans a list of values.
    Strips whitespace from the beginning and end of each value.

    Parameters
    ----------
    values: List[Union[:class:`str`, :class:`bytes`]]
        The values to clean.

    Returns
    -------
    List[Union[:class:`str`, :class:`bytes`]]
        The cleaned values.
    """
    
    return [value.strip() for value in values if value.strip()]

def unwrap_function(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    Unwraps a function.

    Parameters
    ----------
    func: Callable[..., Any]
        The function to unwrap.
    """
    while True:
        if hasattr(func, '__wrapped__'):
            func = func.__wrapped__
        elif isinstance(func, functools.partial):
            func = func.func
        else:
            return func

def iscoroutinefunction(obj: Any) -> bool:
    """
    Checks if a given object is a coroutine function.

    Parameters
    ----------
    obj: Any
        The object to check.
    """
    obj = unwrap_function(obj)
    return asyncio.iscoroutinefunction(obj)

def isasyncgenfunction(obj: Any) -> bool:
    """
    Checks if a given object is an async generator function.

    Parameters
    ----------
    obj: Any
        The object to check.
    """
    obj = unwrap_function(obj)
    return inspect.isasyncgenfunction(obj)

def get_union_args(arg: Any) -> Tuple[Any, ...]:
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
        unions = []

        for arg in args:
            unions.extend(get_union_args(arg))

        return tuple(unions)

    elif origin is not None:
        return (origin,)

    return (arg,)

def evaluate_annotation(
    annotation: Any,
    globals: Optional[Dict[str, Any]] = None,
    locals: Optional[Dict[str, Any]] = None,
    stacklevel: int = -1
) -> Any:

    if not globals:
        globals = {}

    if not locals:
        locals = {}

    if stacklevel != -1:
        frame = sys._getframe(stacklevel)

        globals.update(frame.f_globals)
        locals.update(frame.f_locals)

    return eval(annotation, globals, locals)


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
        _, charset = split
        return charset.split('=')[1]

    return None

def copy_docstring(other: Callable[..., Any]) -> Callable[[Callable[P, T]], Callable[P, T]]:
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

def clear_docstring(func: Callable[P, T]) -> Callable[P, T]:
    """
    Clears the docstring of the decorated function.

    Parameters
    ----------
    func: Callable[..., Any]
        The function to clear the docstring of.
    """
    func.__doc__ = ''
    return func

async def maybe_coroutine(func: MaybeCoroFunc[T], *args: Any, **kwargs: Any) -> T:
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
    if iscoroutinefunction(func):
        return await func(*args, **kwargs) # type: ignore

    return func(*args, **kwargs) # type: ignore

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

def validate_ip(ip: str = None, *, ipv6: bool = False) -> str:
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

@overload
def jsonify(response: JSONResponseBody, **kwargs: Any) -> str:
    ...
@overload
def jsonify(**kwargs: Any) -> str:
    ...
def jsonify(*args: Any, **kwargs: Any) -> str:
    """
    A helper function that returns a JSON string from given arguments.

    Parameters
    ----------
    response: Optional[Union[:class:`dict`, :class:`list`]]
        The response to convert to JSON.
    **kwargs: Any
        Keyword arguments to pass to the JSON encoder.

    Returns
    -------
    :class:`str`
        The JSON string.
    """
    if args:
        response = args[0]

        if isinstance(response, list):
            if kwargs:
                ret = 'Missmatch between response and kwargs. Got list as response while kwargs is a dict'
                raise ValueError(ret)

            return json.dumps(response)

        kwargs.update(response)

    return json.dumps(kwargs)

def parse_headers(raw_headers: bytes) -> Iterator[Header]:
    for line in raw_headers.split(b'\r\n'):
        if not line:
            break
        name, _, value = line.partition(b':')

        if not value:
            continue

        yield Header(name.decode().strip(), value.decode().strip())

@overload
def parse_http_data(data: bytes) -> StripedResult:
    ...
@overload
def parse_http_data(data: bytes, *, strip_status_line: Literal[False]) -> NonStripedResult:
    ...
@overload
def parse_http_data(data: bytes, *, strip_status_line: Literal[True]) -> StripedResult:
    ...
def parse_http_data(data: bytes, *, strip_status_line: bool = True) -> Any:
    end = data.find(b'\r\n\r\n') + 4
    headers, body = data[:end], data[end:]

    status_line, raw_headers = None, headers
    if strip_status_line:
        status_line, raw_headers = headers.split(b'\r\n', 1)
        status_line = status_line.decode()

    return ParsedResult(
        status_line=status_line,
        body=body,
        headers=dict(parse_headers(raw_headers))
    )


def warn(message: str, category: Type[Warning], stacklevel: int = 4):
    warnings.simplefilter('always', category)
    warnings.warn(message, category, stacklevel)

    warnings.simplefilter('default', category)

def deprecated(other: Optional[str] = None):
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

def __dataclass_transform__(
    *,
    eq_default: bool = True,
    order_default: bool = False,
    kw_only_default: bool = False,
    field_descriptors: Tuple[Union[type, Callable[..., Any]], ...] = (()),
) -> Callable[[T], T]:
    return lambda a: a
