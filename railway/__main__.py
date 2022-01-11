
import importlib
import sys
from typing import Any, List, Type
import argparse

from .app import Application

def get(iterable: List[str], index: int) -> str:
    try:
        return iterable[index]
    except IndexError:
        return ''

def create_argument(parser: argparse.ArgumentParser, *names: str, type: Type[Any]) -> None:
    parser.add_argument(*names, type=type, required=False, default=None)

def create_arguments() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Railway')

    create_argument(parser, '--host', type=str)
    create_argument(parser, '--port', '-p', type=int)
    create_argument(parser, '--path', '-P', type=str)
    create_argument(parser, '--worker-count', type=int)

    return parser

def import_from_string(string: str) -> Application:
    parts = string.rsplit('.', 1)

    if len(parts) == 1:
        file = parts[0]
        module = importlib.import_module(file)

        for value in module.__dict__.values():
            if isinstance(value, Application):
                return value
        
        raise RuntimeError('No application instance found in module')
    elif len(parts) == 2:
        file, var = parts
        module = importlib.import_module(file)

        try:
            app = getattr(module, var)
        except AttributeError:
            raise ValueError('Invalid application variable')

        if callable(app):
            app = app()

        if not isinstance(app, Application):
            raise TypeError('Expected Application but got {0} instead.'.format(app.__class__.__name__))

        return app
    else:
        raise ValueError('Invalid application string')

def main() -> None:
    app = import_from_string(get(sys.argv, 1))
    parser = create_arguments()

    args = parser.parse_args(sys.argv[2:])

    if args.host is not None:
        app.host = args.host
    
    if args.port is not None:
        app.port = args.port

    if args.path is not None:
        app.path = args.path

    if args.worker_count is not None:
        app._workers.clear()

        app.worker_count = args.worker_count
        app.setup_workers()

    try:
        app.run()
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    main()