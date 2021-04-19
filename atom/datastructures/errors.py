
__all__ = (
    'MultipleValuesFound',
    'MissingHeader'
)

class MultipleValuesFound(LookupError):
    ...

class HeaderNotFound(KeyError):
    ...

