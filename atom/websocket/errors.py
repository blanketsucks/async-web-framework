from atom.errors import AtomException

__all__ = (
    'WebsocketError',
    'InvalidHandshake'
)

class WebsocketError(AtomException):
    ...

class InvalidHandshake(WebsocketError):
    def __init__(self, **kwargs) -> None:
        self.message = kwargs.get('message', '')
        super().__init__(self.message)
