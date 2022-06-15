from typing import Any, Dict, Optional, Tuple, Type
from inspect import Parameter

from .models import Model

class RailwayException(Exception):
    """Base inheritance class for errors that occur during the Application's runtime."""

class RouteNotFound(RailwayException):
    """Raised when a route is not found."""
    def __init__(self, path: str) -> None:
        super().__init__(f'Route {path!r} not found')
    
class RequestMiddlewareFailed(RailwayException):
    """Raised when a request middleware fails."""

class FailedConversion(RailwayException):
    def __init__(self, argument: Any, parameter: Parameter):
        self.argument = argument
        self.parameter = parameter

        super().__init__(f'Failed to conversion for {parameter.name!r}')

class BadLiteralArgument(FailedConversion):
    def __init__(self, argument: str, parameter: Parameter, expected: Tuple[str, ...]) -> None:
        self.expected = expected
        super().__init__(argument, parameter)

    def __str__(self) -> str:
        return f'Expected one of {self.expected!r}, but got {self.argument!r} instead'

class BadModelConversion(FailedConversion):
    def __init__(self, argument: Dict[str, Any], parameter: Parameter, expected: Tuple[Type[Model], ...]) -> None:
        self.expected = expected
        super().__init__(argument, parameter)

    def __str__(self) -> str:
        names = ', '.join([f'{model.__name__!r}' for model in self.expected])
        return f'Could not convert {self.parameter.name!r} to any of the following models {names}'

class RegistrationError(RailwayException):
    pass

class PartialRead(RailwayException):
    def __init__(self, partial: bytes, expected: Optional[int]) -> None:
        self.partial = partial
        self.length = len(partial)
        self.expected = 'unspecified' if expected is None else str(expected)

        super().__init__(f'Expected a total of {self.expected} bytes, but only got {self.length}')