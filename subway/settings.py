from typing import Any, Dict, Literal, Optional, TypedDict, Union, overload
import importlib
import os
import ssl
import multiprocessing
import json as _json

from .utils import LOCALHOST, LOCALHOST_V6, SETTING_ENV_PREFIX, validate_ip
from .types import StrPath

__all__ = (
    'Settings',
)

class SettingsDict(TypedDict):
    host: Optional[str]
    port: int
    path: Optional[str]
    url_prefix: Optional[str]
    ssl_context: Optional[ssl.SSLContext]
    use_ipv6: bool
    worker_count: int
    session_cookie_name: str
    backlog: int

class Settings:
    __slots__ = (
        'host', 'port', 'path', 'url_prefix',
        'use_ipv6', 'ssl_context', 'worker_count',
        'session_cookie_name', 'backlog'
    )

    def __init__(
        self,
        *,
        host: Optional[str] = None,
        port: Optional[int] = None,
        path: Optional[str] = None,
        url_prefix: Optional[str] = None,
        use_ipv6: bool = False,
        ssl_context: Optional[ssl.SSLContext] = None,
        worker_count: Optional[int] = None,
        session_cookie_name: Optional[str] = None,
        backlog: Optional[int] = None
    ):
        self.host = host
        self.path = path
        self.url_prefix = url_prefix
        self.use_ipv6 = use_ipv6
        self.ssl_context = ssl_context

        if port is not None:
            if not isinstance(port, int):
                raise TypeError('port must be an integer')

            if 0 > port > 65535:
                raise ValueError('port must be in range 0-65535')
        else:
            port = 8080
        self.port = port

        if worker_count is not None:
            if not isinstance(worker_count, int) or worker_count < 0:
                raise TypeError('worker_count must be a positive integer')
        else:
            worker_count = (multiprocessing.cpu_count() * 2) + 1
        self.worker_count = worker_count

        if session_cookie_name is not None:
            if not isinstance(session_cookie_name, str):
                raise TypeError('session_cookie_name must be a str')
        else:
            session_cookie_name = '__subway'
        self.session_cookie_name = session_cookie_name

        if backlog is not None:
            if not isinstance(backlog, int) or backlog < 0:
                raise TypeError('backlog must be a positive integer')
        else:
            backlog = 200
        self.backlog = backlog

        self.ensure_host()

    @overload
    def __getitem__(self, item: Literal['host', 'path']) -> Optional[str]:
        ...
    @overload
    def __getitem__(self, item: Literal['port', 'worker_count', 'backlog']) -> int:
        ...
    @overload
    def __getitem__(self, item: Literal['session_cookie_name']) -> str:
        ...
    @overload
    def __getitem__(self, item: Literal['use_ipv6']) -> bool:
        ...
    @overload
    def __getitem__(self, item: Literal['ssl_context']) -> Optional[ssl.SSLContext]:
        ...
    def __getitem__(self, item: str):
        try:
            return self.__getattribute__(item)
        except AttributeError:
            raise KeyError(item) from None

    @overload
    def __setitem__(self, key: Literal['host', 'path', 'session_cookie_name'], value: str):
        ...
    @overload
    def __setitem__(self, key: Literal['port', 'worker_count', 'backlog'], value: int):
        ...
    @overload
    def __setitem__(self, key: Literal['use_ipv6'], value: bool):
        ...
    @overload
    def __setitem__(self, key: Literal['ssl_context'], value: ssl.SSLContext):
        ...
    def __setitem__(self, key: str, value: Any) -> None:
        return self.__setattr__(key, value)

    @classmethod
    def from_env(cls):
        kwargs = {}
        env = os.environ
        settings = cls.__slots__ # silly thing to do, but it works

        for setting in settings:
            name = SETTING_ENV_PREFIX + setting.casefold()
            kwargs[setting] = env.get(name)

        return cls(**kwargs)

    @classmethod
    def from_file(cls, path: StrPath):
        module = importlib.import_module(str(path))

        kwargs = {}
        settings = cls.__slots__

        for setting in settings:
            value = getattr(module, setting.casefold(), None)
            kwargs[setting] = value

        return cls(**kwargs)

    @classmethod
    def from_json(cls, json: Union[StrPath, Dict[str, Any]]):
        if isinstance(json, (str, os.PathLike)):
            with open(json, 'r') as f:
                data = _json.load(f)
        else:
            data = json

        return cls(**data)
        
    def ensure_host(self) -> None:
        if self.path is not None:
            return None

        if self.use_ipv6:
            if not self.host:
                self.host = LOCALHOST_V6
            else:
                validate_ip(self.host, ipv6=True)
        else:
            if not self.host:
                self.host = LOCALHOST
            else:
                validate_ip(self.host)

        return None

    def to_dict(self) -> SettingsDict:
        return {
            'host': self.host,
            'port': self.port,
            'path': self.path,
            'url_prefix': self.url_prefix,
            'use_ipv6': self.use_ipv6,
            'ssl_context': self.ssl_context,
            'worker_count': self.worker_count,
            'session_cookie_name': self.session_cookie_name,
            'backlog': self.backlog
        }

class Config(dict):
    pass