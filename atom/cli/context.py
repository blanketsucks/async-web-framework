import typing

if typing.TYPE_CHECKING:
    from .core import Command

class Context:
    def __init__(self, command: 'Command', args: typing.Tuple) -> None:
        self.command = command
        self.args = args

    async def invoke(self, args: typing.Tuple):
        result = await self.command.func(self, *args)
        return result

    def __repr__(self) -> str:
        return '<Context command={0.command!r}>'.format(self)