
from typing import Tuple
from railway.errors import RailwayException

class SQLAlchemyException(RailwayException):
    pass

class EngineException(SQLAlchemyException):
    pass

class InvalidDatabase(EngineException):
    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f'{name!r} is not supported')

class InvalidDialect(EngineException):
    def __init__(self, dialect: str) -> None:
        self.dialect = dialect
        super().__init__(f'{dialect!r} is not supported')

class NoDriverFound(EngineException):
    def __init__(self, drivers: Tuple[str, ...]):
        self.drivers = drivers
        super().__init__(f'Could not find any of the following drivers: {", ".join(drivers)}')