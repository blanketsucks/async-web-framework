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
from typing import Any, Dict, Union, Optional, TypedDict
import importlib
import os
import pathlib
import ssl
import multiprocessing

from .utils import LOCALHOST, LOCALHOST_V6, SETTING_ENV_PREFIX, is_ipv6

__all__ = (
    'Settings',
    'DEFAULT_SETTINGS',
    'settings_from_file',
    'settings_from_env',
    'VALID_SETTINGS',
)

VALID_SETTINGS = (
    'host',
    'port',
    'use_ipv6',
    'ssl_context',
    'worker_count'
)

DEFAULT_SETTINGS = {
    'host': LOCALHOST,
    'port': 8080,
    'url_prefix': '',
    'use_ipv6': False,
    'ssl_context': None,
    'worker_count': (multiprocessing.cpu_count() * 2) + 1,
    'session_cookie_name': '__railway',
    'backlog': 200,
    'max_concurrent_requests': None,
    'max_pending_connections': None,
    'connection_timeout': None    
}

class Settings(TypedDict):
    """
    A :class:`typing.TypedDict` representing settings used by the application.
    """
    host: str
    port: int
    url_prefix: str
    use_ipv6: bool
    ssl_context: Optional[ssl.SSLContext]
    worker_count: int
    session_cookie_name: str
    backlog: int
    max_concurrent_requests: Optional[int]
    max_pending_connections: int
    connection_timeout: Optional[int]

def settings_from_file(path: Union[str, pathlib.Path]) -> Settings:
    """
    Loads settings from a file.

    Parameters
    ----------
    path: Union[:class:`str`, :class:`pathlib.Path`]
        The path of the file to load settings from.
    """
    if isinstance(path, pathlib.Path):
        path = str(path)

    module = importlib.import_module(path)

    kwargs: Dict[str, Any] = {}
    
    for key, default in DEFAULT_SETTINGS.items():
        value = getattr(module, key.casefold(), default)
        kwargs[key] = value

    if kwargs['use_ipv6'] and not is_ipv6(kwargs['host']):
        kwargs['host'] = LOCALHOST_V6

    settings = Settings(**kwargs)
    return settings

def settings_from_env() -> Settings:
    """
    Loads settings from environment variables.

    Returns:
        A [Settings](./settings.md) object.
    """
    env = os.environ
    kwargs = {}

    for key, default in DEFAULT_SETTINGS.items():
        item = SETTING_ENV_PREFIX + key.casefold()
        kwargs[key] = env.get(item, default)

    if kwargs['use_ipv6'] and not is_ipv6(kwargs['host']):
        kwargs['host'] = LOCALHOST_V6

    settings = Settings(**kwargs)
    return settings
