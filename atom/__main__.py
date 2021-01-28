
import argparse
import importlib

from .app import Application
from .restful import App


def import_from_string(string: str):
    if len(string.split(':')) > 2:
        raise TypeError('Invalid input. {file}:{app_variable}')

    file, var = string.split(':')

    module = importlib.import_module(file)

    try:
        app = getattr(module, var)
    except AttributeError:
        raise TypeError('Invalid application variable.')

    if not isinstance(app, (Application, App)):
        raise TypeError('Expected Application or App but got {0} instead.'.format(app.__class__.__name__))

    return app

def prepare_parser(prog):
    parser = argparse.ArgumentParser(prog=prog)

    parser.add_argument('app', type=str)
    parser.add_argument('--host', type=str, required=False)

    parser.add_argument('--port', type=int, required=False)
    parser.add_argument('--debug', type=bool, required=False)

    return parser

def prepare_arguments(host, port, debug):
    kwargs = {
        'host': host,
        'port': port,
        'debug': debug
    }
    return kwargs

def main():
    parser = prepare_parser('ASGI')
    args = parser.parse_args()

    app = import_from_string(args.app)
    kwargs = prepare_arguments(args.host, args.port, args.debug)

    app.run(**kwargs)


if __name__ == '__main__':
    main()
