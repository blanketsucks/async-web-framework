from atom.errors import AtomException

__all__ = (
    'CLIException',
    'CommandError',
    'CommandInvokationError',
    'FailedConversion',
    'MissingArgument',
    'MissingContextArgument'
)

class CLIException(AtomException):
    ...

class CommandError(CLIException):
    ...

class CommandInvokationError(CommandError):
    ...

class FailedConversion(CommandInvokationError):
    def __init__(self, cls, key) -> None:
        fmt = 'Failed conversion for {0!r} to {1}'
        super().__init__(fmt.format(key, cls))

class MissingArgument(CommandInvokationError):
    def __init__(self, key: str) -> None:
        fmt = '{0!r} is a required argument that is missing.'
        super().__init__(fmt.format(key))

class MissingContextArgument(CommandInvokationError):
    def __init__(self, command) -> None:
        super().__init__(f'{command.name!r} is missing the Context argument')