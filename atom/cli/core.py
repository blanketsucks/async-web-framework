import asyncio
import sys
import typing
import tokenize


from .context import Context

class Option:
    def __init__(self, name: str, *, required: bool=False, type: object) -> None:
        self.name = name
        self.required = required

        self.type = type

    def parse(self, args: typing.Tuple):
        for arg in args:
            if self.name == arg:
                return self.type(arg)

        if not self.required:
            return None

        raise TypeError(f'Missing {self.name!r} argument.')

class Group:
    def __init__(self, name: str=None, *, loop: asyncio.AbstractEventLoop=None) -> None:
        self.name = name
        self.loop = loop or asyncio.get_event_loop()

        self._commands = {}

    @property
    def commands(self):
        return self._commands

    def command(self, name: str=None, **kwargs):
        def wrapper(func):
            actual = name

            if not actual:
                actual = func.__name__

            cmd = Command(func, actual, **kwargs)
            self._commands[cmd.name] = cmd

            return cmd
        return wrapper

    def parse(self):
        args = sys.argv[1:]
        try:
            name = args[0]
        except IndexError:
            return

        args.remove(name)
        args = tuple(args)

        command: Command = self._commands.get(name)
        options = command.options

        ctx = Context(command, args)
        if command:
            return self.loop.run_until_complete(ctx.invoke())

        return

class Command:
    def __init__(self, 
                func: typing.Callable, 
                name: str, 
                *, 
                options: typing.Iterable[Option]=None, 
                help: str=None, 
                usage: str=None) -> None:

        self.name = name
        self.func = func

        if not help:
            self.help = func.__doc__
        else:
            self.help = help

        self.usage = usage
        self.options = options

    def __repr__(self) -> str:
        return '<Command name={0.name!r}>'.format(self)