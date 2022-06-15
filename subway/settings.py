from typing import Any, Dict, Optional, TypedDict, Union
import importlib
import os
import ssl as _ssl
import multiprocessing

from .utils import LOCALHOST, LOCALHOST_V6, SETTING_ENV_PREFIX, validate_ip, loads
from .types import StrPath

__all__ = (
    'Settings',
)

def default_ssl_context():
    context = _ssl.create_default_context(purpose=_ssl.Purpose.CLIENT_AUTH)
    return context

class SettingsDict(TypedDict):
    host: Optional[str]
    port: int
    path: Optional[str]
    ssl: Optional[_ssl.SSLContext]
    ipv6: bool
    worker_count: int
    session_cookie_name: str
    backlog: int

class Settings:
    __slots__ = (
        'host', 'port', 'path', 'ipv6', 'ssl', 'worker_count', 'session_cookie_name', 'backlog'
    )

    def __init__(
        self,
        *,
        host: Optional[str] = None,
        port: Optional[int] = None,
        path: Optional[str] = None,
        ipv6: bool = False,
        ssl: Union[bool, _ssl.SSLContext] = False,
        worker_count: Optional[int] = None,
        session_cookie_name: Optional[str] = None,
        backlog: Optional[int] = None
    ):
        self.host = host
        self.path = path
        self.ipv6 = ipv6
        self.ssl = ssl if isinstance(ssl, _ssl.SSLContext) else default_ssl_context() if ssl else None

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

    def __getitem__(self, item: str):
        try:
            return self.__getattribute__(item)
        except AttributeError:
            raise KeyError(item) from None

    def __setitem__(self, key: str, value: Any) -> None:
        return self.__setattr__(key, value)

    @classmethod
    def from_env(cls):
        kwargs = {}
        env = os.environ
        settings = cls.__slots__

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
    def from_json(cls, data: Union[StrPath, Dict[str, Any]]):
        if isinstance(data, (str, os.PathLike)):
            with open(data, 'r') as f:
                value = loads(f.read())
        else:
            value = data

        return cls(**value)
        
    def ensure_host(self) -> None:
        if self.path is not None:
            return None

        if self.ipv6:
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

    def update(
        self, 
        *,
        host: Optional[str] = None,
        port: Optional[int] = None,
        path: Optional[str] = None,
        ipv6: bool = False,
        ssl: Union[bool, _ssl.SSLContext] = False,
        worker_count: Optional[int] = None,
        session_cookie_name: Optional[str] = None,
        backlog: Optional[int] = None
    ) -> None:
        if host is not None:
            self.host = host
        if port is not None:
            self.port = port
        if path is not None:
            self.path = path
        if ssl is not None:
            self.ssl = ssl if isinstance(ssl, _ssl.SSLContext) else default_ssl_context() if ssl else None
        if worker_count is not None:
            self.worker_count = worker_count
        if session_cookie_name is not None:
            self.session_cookie_name = session_cookie_name
        if backlog is not None:
            self.backlog = backlog

        self.ipv6 = ipv6 or self.ipv6
        self.ensure_host()

    def to_dict(self) -> SettingsDict:
        return {
            'host': self.host,
            'port': self.port,
            'path': self.path,
            'ipv6': self.ipv6,
            'ssl': self.ssl,
            'worker_count': self.worker_count,
            'session_cookie_name': self.session_cookie_name,
            'backlog': self.backlog
        }

class Config(dict):
    pass