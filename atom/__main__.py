
import argparse
import importlib

from . import cli
from .app import Application

group = cli.Group()

def import_from_string(string: str):
    if len(string.split(':')) > 2:
        raise TypeError('Invalid input. {file}:{app_variable}')

    file, var = string.split(':')

    module = importlib.import_module(file)

    try:
        app = getattr(module, var)
    except AttributeError:
        raise TypeError('Invalid application variable.')

    if not isinstance(app, (Application)):
        raise TypeError('Expected Application or App but got {0} instead.'.format(app.__class__.__name__))

    return app

def prepare_parser(prog):
    parser = argparse.ArgumentParser(prog=prog)

    parser.add_argument('app', type=str)
    parser.add_argument('--host', type=str, required=False)

    parser.add_argument('--port', type=int, required=False)
    parser.add_argument('--debug', type=bool, required=False)

    return parser

option = cli.Option('--filename', type=str)

@group.command(name='run', options=(option,))
async def run(ctx: cli.Context, filename: str):
    """Runs the application"""
    print(filename)


if __name__ == '__main__':
    group.parse()
