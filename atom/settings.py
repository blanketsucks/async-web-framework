import importlib
import typing
import os
import pathlib

from .errors import InvalidSetting
from .utils import DEFAULT_SETTINGS, VALID_SETTINGS, SETTING_ENV_PREFIX

__all__ = (
    'Settings',
)

class Settings(dict):
    def __init__(self, settings_file: typing.Union[str, pathlib.Path]=None, load_env: bool=False):

        if load_env:
            self.from_env_vars()

        if settings_file:
            self.from_file(settings_file)

        super().__init__(**DEFAULT_SETTINGS)

    def __setitem__(self, k, v) -> None:
        if k not in VALID_SETTINGS:
            raise InvalidSetting(f'{k} is not a valid setting.')

        return super().__setitem__(k, v)

    def __setattr__(self, name: str, value) -> None:
        if name not in VALID_SETTINGS:
            raise InvalidSetting(f'{name} is not a valid setting.')

        self[name] = value

    def __getattr__(self, name: str):
        try:
            value = self[name]
        except KeyError:
            raise InvalidSetting(f'{name} is not a valid setting.') from None

        return value

    def from_file(self, fp: typing.Union[str, pathlib.Path]):
        if isinstance(fp, pathlib.Path):
            fp = fp.name

        module = importlib.import_module(fp)
        for name, value in module.__dict__.items():
            if name in VALID_SETTINGS:
                self[name] = value
                
        return self

    def from_env_vars(self):
        envs = os.environ

        for name, value in envs.items():
            if name.startswith(SETTING_ENV_PREFIX):
                prefix, key = name.split(SETTING_ENV_PREFIX, maxsplit=1)

                if key in VALID_SETTINGS:
                    self[key] = value

                else:
                    raise InvalidSetting(f'{key} is not a valid setting.')

        return self 

