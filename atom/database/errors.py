from atom.errors import AtomException

__all__ = (
    'DatabaseError',
    'NoConnections'
)

class DatabaseError(AtomException):
    ...

class NoConnections(DatabaseError):
    ...