from typing import Dict, Type, Union, Optional, TypedDict
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
    'use_ipv6': False,
    'ssl_context': None,
    'worker_count': (multiprocessing.cpu_count() * 2) + 1,
    'session_cookie_name': None,
}

class Settings(TypedDict):
    """
    A `typing.TypedDict` representing settings used by the application.

    Attributes:
        host: The hostname or IP address to listen on.
        port: The port to listen on.
        use_ipv6: Whether to use IPv6.
        ssl_context: The SSL context to use.
        worker_count: The number of workers to use.
    """
    host: str
    port: int
    use_ipv6: bool
    ssl_context: Optional[ssl.SSLContext]
    worker_count: int
    session_cookie_name: Optional[str]

def settings_from_file(path: Union[str, pathlib.Path]) -> Settings:
    """
    Loads settings from a file.

    Args:
        path: The path to the file.

    Returns:
        A [Settings](./settings.md) object.
    """
    if isinstance(path, pathlib.Path):
        path = str(path)

    module = importlib.import_module(path)

    kwargs = {}
    
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
