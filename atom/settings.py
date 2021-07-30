from typing import Dict, Union, Optional
import importlib
import os
import pathlib

from .errors import InvalidSetting
from .utils import SETTING_ENV_PREFIX

__all__ = (
    'Settings',
)

_BASE_SETTINGS = {
    'HOST': '127.0.0.1',
    'PORT': 8080,
    'COOKIE_SESSION_NAME': None
}

class Crendentials:
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

class Authentication:
    def __init__(self):
        self._creditials: Dict[str, Crendentials] = {}

    def set_credentials_for(self, 
                            service: str, 
                            *, 
                            client_id: str, 
                            client_secret: str, 
                            redirect_uri: str) -> None:
        credentials = Crendentials(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri
        )
        self._creditials[service] = credentials
        return credentials

    def get_credentials_for(self, service: str) -> Optional[Crendentials]:
        return self._creditials.get(service)

    def __iter__(self):
        yield from self._creditials.items()

class Settings(dict):
    def __init__(self):
        self.authentication = Authentication()
        super().__init__(**_BASE_SETTINGS)

    def __getitem__(self, k: str):
        return self.get(k.upper())

    @classmethod
    def from_file(cls, fp: Union[str, pathlib.Path]):
        self = cls()
        if isinstance(fp, pathlib.Path):
            fp = fp.name

        module = importlib.import_module(fp)
        for name, value in module.__dict__.items():
            pass
                
        return self

    @classmethod
    def from_env_vars(cls):
        self = cls()
        envs = os.environ

        for name, value in envs.items():
            if name.startswith(SETTING_ENV_PREFIX):
                prefix, key = name.split(SETTING_ENV_PREFIX, maxsplit=1)

        return self

    def __repr__(self) -> str:
        return '<Settings>'
