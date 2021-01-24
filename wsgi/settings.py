
import importlib
import typing

class Settings(dict):
    def __init__(self, *args, **kwargs):
        self.VALID_SETTINGS: typing.Tuple[str] = (
            'SECRET_KEY',
            'DEBUG'
        )

        super().__init__(*args, **kwargs)

    def __setitem__(self, k, v) -> None:
        if not k in self.VALID_SETTINGS:
            raise ValueError(f'{k} is not a valid setting.')

        return super().__setitem__(k, v)

    def from_file(self, fp: str) -> typing.Optional[typing.Dict[str, typing.Any]]:
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
