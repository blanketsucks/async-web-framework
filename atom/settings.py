from typing import Dict, Union, Optional
import importlib
import os
import pathlib

from .utils import SETTING_ENV_PREFIX
from .datastructures import ImmutableMapping

__all__ = (
    'Settings',
)

class Settings(ImmutableMapping[str, Union[str, int, bool]]):
    def __init__(self, defaults: Optional[Dict[str, Union[str, int, bool]]]=None) -> None:
        if not defaults:
            defaults = {}

        super().__init__(**defaults)

    def __getitem__(self, k: str):
        return super().__getitem__(k.upper())

    @classmethod
    def from_file(cls, fp: Union[str, pathlib.Path]):
        self = cls()
        if isinstance(fp, pathlib.Path):
            fp = fp.name

        importlib.import_module(fp)      
        return self

    @classmethod
    def from_env_vars(cls):
        self = cls()
        envs = os.environ

        for name, _ in envs.items():
            if name.startswith(SETTING_ENV_PREFIX):
                _, _ = name.split(SETTING_ENV_PREFIX, maxsplit=1)

        return self

    def __repr__(self) -> str:
        return '<Settings>'
