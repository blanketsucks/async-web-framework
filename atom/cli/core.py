import typing


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

    def __call__(self, *args):
        return self.func(*args)

    @property
    def args(self) -> typing.List[str]:
        return list(self.func.__code__.co_varnames)

    def __repr__(self) -> str:
        return '<Command name={0.name!r}>'.format(self)