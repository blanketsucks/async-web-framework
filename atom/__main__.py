
import argparse
import importlib
import typing

from . import cli
from .app import Application

atom = cli.CLI()

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

option = cli.Option('--filename', type=str)

@atom.command(name='run', options=(option,))
def run(ctx: cli.Context, filename: str, host: typing.Optional[str], port: typing.Optional[int]):
    """Runs the application"""

    app = import_from_string(filename)

    if not host:
        host = '127.0.0.1'

    if not port:
        port = 8080

    app.run(host, port=port)

if __name__ == '__main__':
    atom.parse()
