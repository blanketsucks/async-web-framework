from .core import Command
from .context import Context
from .errors import *

import sys
import typing
import asyncio

class CLI:
    def __init__(self, name: str=None) -> None:
        self.name = name

        self._commands = {}

    @property
    def commands(self):
        return self._commands

    def add_command(self, func, name: str=None, **kwargs):
        name = func.__name__ if not name else name

        command = Command(func, name, **kwargs)
        self._commands[name] = command

        return command

    def command(self, name: str=None, **kwargs):
        def wrapper(func):
            return self.add_command(func, name, **kwargs)
        return wrapper

    def _prepare_arguments(self, command: Command, argv: typing.List):
        args = command.args.copy()
        args.pop(0)

        kwargs = {}
        for i in range(len(args)):
            arg = args[i]

            try:
                value = argv[i]
            except IndexError:
                continue

            kwargs[arg] = value

        return kwargs

    def _do_optional_conversion(self, arg: str, cls: object, value: typing.Any=None):
        if not value:
            return None

        try:
            return cls(value)
        except ValueError:
            raise FailedConversion(cls, arg)

    def _convert(self, command: Command, args: typing.Dict):
        annotations = command.func.__annotations__

        try:
            del annotations['ctx']
        except KeyError:
            try:
                del annotations['context']
            except KeyError as exc:
                raise MissingContextArgument(command) from exc

        converted = {}

        for key, value in annotations.items():
            item = args.get(key)
            value_args = getattr(value, '__args__', None)

            if value_args and type(None) in value.__args__:
                cls = value.__args__[0]
                converted[key] = self._do_optional_conversion(key, cls, item)

                continue

            try:
                converted[key] = value(item)
            except ValueError:
                raise FailedConversion(cls, key)
        
        return converted

    def parse(self):
        args = sys.argv[1:]
        try:
            name = args[0]
        except IndexError:
            return

        args.remove(name)

        command: Command = self._commands.get(name)

        if not command:
            return

        kwargs = self._prepare_arguments(command, args)
        converted = self._convert(command, kwargs)

        ctx = Context(command, args)
        return ctx.invoke(**converted)