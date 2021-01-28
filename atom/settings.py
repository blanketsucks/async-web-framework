import importlib
import typing
import pathlib

from .error import InvalidSetting

class Settings(dict):
    def __init__(self, *args, **kwargs):
        self.VALID_SETTINGS: typing.Tuple = (
            'SECRET_KEY',
            'DEBUG'
        )

        super().__init__(*args, **kwargs)

    def __setitem__(self, k, v) -> None:
        if k not in self.VALID_SETTINGS:
            raise InvalidSetting(f'{k} is not a valid setting.')

        return super().__setitem__(k, v)

    def from_file(self, fp: typing.Union[str, pathlib.Path]) -> typing.Optional[typing.Dict[str, typing.Any]]:
        if isinstance(fp, pathlib.Path):
            fp = fp.name

        module = importlib.import_module(fp)
        setting = getattr(module, 'load_settings')

        if not setting:
            return None

        res = setting()

        for k, v in res.items():
            self[k] = v

        return res

    def reset_all(self):
        for k in self.keys():
            del self[k]
