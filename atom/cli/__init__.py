from .core import Command, Group, Option
from .context import Context

def command(group: Group, name: str=None, **kwargs):
    def wrapper(func):
        actual = name

        if not actual:
            actual = func.__name__

        cmd = Command(func, actual, **kwargs)
        group._commands[cmd.name] = cmd

        return cmd
    return wrapper