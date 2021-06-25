import importlib
import sys

from .app import Application

def import_from_string(string: str):
    if len(string.split(':')) > 2:
        raise TypeError('Invalid input. {file}:{app_variable}')

    file, var = string.split(':')
    module = importlib.import_module(file)

    try:
        app = getattr(module, var)
    except AttributeError:
        raise TypeError('Invalid application variable.')

    if not isinstance(app, Application):
        raise TypeError('Expected Application or App but got {0} instead.'.format(app.__class__.__name__))

    return app

if __name__ == '__main__':
    app = import_from_string(sys.argv[1])
    app.run()
