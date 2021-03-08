from atom.errors import AtomException

__all__ = (
    'ServerError',
    'ConnectionError'
)

class ServerError(AtomException):
    ...

class ConnectionError(ServerError):
    ...
