from atom.errors import AtomException

__all__ = (
    'MultipleValuesFound',
    'MissingHeader'
)

class MultipleValuesFound(AtomException, LookupError):
    ...

class HeaderNotFound(AtomException, KeyError):
    ...

