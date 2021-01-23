
import importlib
import typing

VALID_SETTINGS: typing.Tuple[str] = (
    'SECRET_KEY',
)

class Settings(dict):

    def from_file(self, fp: str) -> typing.Optional[typing.Dict[str, typing.Any]]:
        module = importlib.import_module(fp)
        setting = getattr(module, 'load_settings')

        if not setting:
            return None

        res = setting()
        
        for k, v in res.items():
            if k in VALID_SETTINGS:
                self[k] = v
            else:
                pass

        return res
