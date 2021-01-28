import asyncio
import argparse
import importlib


def main():
    parser = argparse.ArgumentParser(prog='atom')
    loop = asyncio.get_event_loop()

    parser.add_argument('fileapp', type=str)
    parser.add_argument('--host', type=str, required=False)
    parser.add_argument('--port', type=int, required=False)
    parser.add_argument('--debug', type=bool, required=False)

    args = parser.parse_args()
    file, app = args.fileapp.split(':')

    kwargs = {
        'host': args.host,
        'port': args.port,
        'debug': args.debug
    }

    mod = importlib.import_module(file)

    start = getattr(mod, app)
    loop.run_until_complete(start(**kwargs))


if __name__ == '__main__':
    main()
