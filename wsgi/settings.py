
import importlib

VALID_SETTINGS = (
    'SECRET_KEY',
    'CLIENT_SECRET_VALIDATOR'
)


class Settings(dict):

    def from_file(self, fp: str):
        module = importlib.import_module(fp)
        setting = getattr(module, 'load_settings')

        res = setting()
        
        for k, v in res.items():
            if k in VALID_SETTINGS:
                self[k] = v
            else:
                pass
