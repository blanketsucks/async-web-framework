try:
    import sqlalchemy
except ImportError:
    raise RuntimeError('SQLAlchemy is required to use this extension')

try:
    import greenlet
except ImportError:
    raise RuntimeError('Greenlet is required to use this extension')
