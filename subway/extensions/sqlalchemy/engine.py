from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Dict, Generator, Tuple, Type, TypeVar, Union, Optional, List
from sqlalchemy.ext.asyncio import create_async_engine, AsyncConnection, AsyncEngine
from sqlalchemy.engine.interfaces import Dialect as _Dialect
from sqlalchemy.ext.asyncio.engine import AsyncTransaction
from sqlalchemy.engine.url import make_url, URL as _URL
from sqlalchemy.sql import ClauseElement, text
import importlib
import sys

from .errors import InvalidDatabase, InvalidDialect, NoDriverFound
from .results import CursorResult, Row

class Dialect(_Dialect):
    is_async: bool

class URL(_URL):
    if TYPE_CHECKING:
        def get_dialect(self) -> Dialect: ...
        def set(self, **kwargs: Any) -> URL: ...

__all__ = (
    'Engine',
    'Connection',
    'Transaction',
    'create_engine',
    'create_connection',
)

if TYPE_CHECKING:
    from typing_extensions import ParamSpec

    P = ParamSpec('P')
    T = TypeVar('T')
    
EngineT = TypeVar('EngineT', bound='Engine')

class TransactionContext:
    transaction: Transaction
    def __init__(self, connection: Connection) -> None:
        self.connection = connection

    async def start(self) -> Transaction:
        if not self.connection.connected:
            await self.connection.start()

        self.transaction = self.connection.transaction()
        return self.transaction

    def __await__(self):
        return self.start().__await__()

    async def __aenter__(self) -> Connection:
        transaction = await self.start()
        await transaction.__aenter__()

        return self.connection

    async def __aexit__(self, *args):
        await self.transaction.__aexit__(*args)

class Transaction:
    """
    A wrapper around :class:`sqlalchemy.ext.asyncio.AsyncTransaction`.

    Attributes
    ----------
    wrapped: :class:`sqlalchemy.ext.asyncio.AsyncTransaction`
        The wrapped transaction.
    connection: :class:`~.Connection`
        The connection that this transaction is associated with.
    connected: :class:`bool`
        Whether or not this transaction is connected.
    """
    def __init__(self, transaction: AsyncTransaction, connection: Connection) -> None:
        self.wrapped = transaction
        self.connection = connection
        self.connected = False

    def check_connected(self) -> None:
        if not self.connected:
            raise Exception('Transaction is not connected')

    @property
    def nested(self) -> bool:
        """
        Whether or not this transaction is nested.
        """
        return self.wrapped.nested

    def is_valid(self) -> bool:
        """
        Whether or not this transaction is valid.
        """
        return self.wrapped.is_valid

    def is_active(self) -> bool:
        """
        Whether or not this connection is active.
        """
        return self.wrapped.is_active

    async def commit(self) -> None:
        """
        Commits the transaction.
        """
        self.check_connected()
        await self.wrapped.commit()

    async def rollback(self) -> None:
        """
        Roll backs the transaction.
        """
        self.check_connected()
        await self.wrapped.rollback()

    async def start(self) -> Transaction:
        """
        Starts the transaction.
        """
        await self.wrapped.start()
        return self

    async def close(self) -> None:
        """
        Closes this connection.
        """
        self.check_connected()
        await self.wrapped.close()

        self.connected = False

    async def __aenter__(self) -> Transaction:
        return await self.start()

    async def __aexit__(self, exc_type: Optional[Type[Exception]], exc_val: Exception, exc_tb: Any) -> None:
        if exc_type is None:
            await self.commit()
        else:
            await self.rollback()

        await self.close()

class Connection:
    """
    A wrapper around :class:`sqlalchemy.ext.asyncio.AsyncConnection`.
    
    Attributes
    ----------
    wrapped: :class:`sqlalchemy.ext.asyncio.AsyncConnection`
        The wrapped connection.
    connected: :class:`bool`
        Whether the connection has started or not.
    """
    def __init__(self, connection: AsyncConnection) -> None:
        self.wrapped = connection
        self.connected = False

    def check_connected(self) -> None:
        if not self.connected:
            raise Exception('Connection is not started')

    def transaction(self) -> Transaction:
        """
        Returns a transaction bound to this connection.
        """
        self.check_connected()
        return Transaction(self.wrapped.begin(), self)

    async def run(self, func: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> T:
        """
        Runs a sync function.

        Parameters
        ----------
        func: Callable
            The function to run.
        *args: Any
            The positional arguments to pass to the function.
        **kwargs: Any
            The keyword arguments to pass to the function.

        Returns
        -------
        Any:
            The return value of the function.
        """
        return await self.wrapped.run_sync(func, *args, **kwargs)

    async def execute(self, query: Union[str, ClauseElement]) -> CursorResult:
        """
        Executes a query.

        Parameters
        ----------
        query: :class:`str` or :class:`sqlalchemy.ClauseElement`
            The query to execute.
        """
        self.check_connected()
        
        if isinstance(query, str):
            query = text(query)

        cursor = await self.wrapped.execute(query)
        return CursorResult(cursor)

    async def fetchall(self, query: Union[str, ClauseElement]) -> List[Row]:
        """
        Fetches all rows from a query.

        Parameters
        ----------
        query: :class:`str` or :class:`sqlalchemy.ClauseElement`
            The query to execute.
        """
        cursor = await self.execute(query)
        return await cursor.fetchall()

    async def fetchone(self, query: Union[str, ClauseElement]) -> Optional[Row]:
        """
        Fetches one row from a query.

        Parameters
        ----------
        query: :class:`str` or :class:`sqlalchemy.ClauseElement`
            The query to execute.
        """
        cursor = await self.execute(query)
        return await cursor.fetchone()

    async def fetchmany(self, query: Union[str, ClauseElement], size: int = 100) -> List[Row]:
        """
        Fetches multiple rows from a query.

        Parameters
        ----------
        query: :class:`str` or :class:`sqlalchemy.ClauseElement`
            The query to execute.
        size: :class:`int`
            The number of rows to fetch.
        """
        cursor = await self.execute(query)
        return await cursor.fetchmany(size)

    async def commit(self) -> None:
        """
        Commits the transaction that is currently in progress.
        """
        self.check_connected()
        await self.wrapped.commit()

    async def close(self) -> None:
        """
        Closes this connection.
        """
        self.check_connected()
        await self.wrapped.close()

        self.connected = True

    async def start(self) -> Connection:
        """
        Starts this connection.
        """
        await self.wrapped.start()

        self.connected = True
        return self

    async def rollback(self) -> None:
        """
        Roll back the transaction that is currently in progress.
        """
        await self.wrapped.rollback()

    def __await__(self) -> Generator[Any, None, Connection]:
        return self.start().__await__()

    async def __aenter__(self) -> Connection:
        return await self.start()

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

class Engine:
    """
    A wrapped around :class:`sqlalchemy.ext.asyncio.AsyncEngine`.

    Attributes
    ----------
    wrapped: :class:`sqlalchemy.ext.asyncio.AsyncEngine`
        The wrapped engine.
    """
    DRIVERS: Dict[str, Tuple[str, ...]] = {
        'sqlite': ('aiosqlite',),
        'postgresql': ('aiopg', 'asyncpg'),
        'mysql': ('aiomysql',),
    }

    def __init__(self, engine: AsyncEngine, url: URL) -> None:
        self.wrapped = engine
        self.url = url

    def __repr__(self) -> str:
        return f'<Engine database={self.database!r} dialect={self.dialect.name!r} driver={self.driver!r}>'

    @classmethod
    def get_optimal_driver(cls, database: str) -> Optional[str]:
        drivers = cls.DRIVERS.get(database)
        if not drivers:
            raise InvalidDatabase(database)

        for driver in drivers:
            if driver in sys.modules:
                return driver

            try:
                importlib.import_module(driver)
            except ImportError:
                continue
            else:
                return driver

        raise NoDriverFound(drivers)

    @classmethod
    def from_url(cls: Type[EngineT], url: str, *args: Any, **kwargs: Any) -> EngineT:
        u: URL = make_url(url) # type: ignore

        try:
            database, driver = u.drivername.split('+')
            drivers = cls.DRIVERS.get(driver)

            if drivers is None:
                raise InvalidDatabase(database)
        except ValueError:
            database = u.drivername
            driver = cls.get_optimal_driver(database)

        drivername = f'{database}+{driver}' if driver else database
        u = u.set(drivername=drivername)

        dialect = u.get_dialect()
        if not dialect.is_async:
            raise InvalidDialect(dialect.name)

        engine = create_async_engine(u, *args, **kwargs)
        return cls(engine, u)

    @property
    def database(self) -> str:
        return self.url.database

    @property
    def dialect(self) -> Dialect:
        return self.url.get_dialect()

    @property
    def driver(self) -> str:
        return self.url.get_driver_name()

    def acquire(self) -> Connection:
        """
        Acquires a connection from the engine.
        """
        return Connection(self.wrapped.connect())

    def transaction(self) -> TransactionContext:
        """
        Returns a transaction context object.
        """
        return TransactionContext(self.acquire())

    async def execute(self, query: Union[str, ClauseElement]) -> CursorResult:
        """
        Executes a query.

        Parameters
        ----------
        query: Union[:class:`str`, :class:`sqlalchemy.ClauseElement`]
            The query to execute.
        *args: Any
            The arguments to pass to the query.
        """
        async with self.acquire() as connection:
            return await connection.execute(query)

    async def fetchall(self, query: Union[str, ClauseElement]) -> List[Row]:
        """
        Fetches all rows from a query.

        Parameters
        ----------
        query: Union[:class:`str`, :class:`sqlalchemy.sql.ClauseElement`]
            The query to execute.
        *args: Any
            The arguments to pass to the query.
        """
        async with self.acquire() as connection:
            return await connection.fetchall(query)

    async def fetchone(self, query: Union[str, ClauseElement]) -> Optional[Row]:
        """
        Fetches one row from a query.

        Parameters
        ----------
        query: Union[:class:`str`, :class:`sqlalchemy.sql.ClauseElement`]
            The query to execute.
        *args: Any
            The arguments to pass to the query.
        """
        async with self.acquire() as connection:
            return await connection.fetchone(query)

    async def fetchmany(self, query: Union[str, ClauseElement], size: int = 100) -> List[Row]:
        """
        Fetches many rows from a query.

        Parameters
        ----------
        query: Union[:class:`str`, :class:`sqlalchemy.sql.ClauseElement`]
            The query to execute.
        *args: Any
            The arguments to pass to the query.
        size: :class:`int`
            The number of rows to fetch.
        """
        async with self.acquire() as connection:
            return await connection.fetchmany(query, size)

    async def close(self) -> None:
        """
        Closes the engine.
        """
        await self.wrapped.dispose()

    async def __aenter__(self) -> Engine:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()
    

def create_engine(url: str, *args: Any, **kwargs: Any) -> Engine:
    """
    Creates an async engine and returns it.

    Parameters
    -----------
    url: :class:`str`
        The database url.
    *args: Any
        Additional arguments.
    **kwargs: Any
        Additional keyword arguments
    """
    return Engine.from_url(url, *args, **kwargs)

def create_connection(url: str, *args: Any, **kwargs: Any) -> Connection:
    """
    Creates an async sqlalchemy connection and returns it.
    Can be used as a context manager and if you don't want to use it,
    you can just await the returned result from this function.

    This offers a nice way to use along the :meth:`~subway.Application.lifespan` functions ::

        @app.lifespan
        async def start_database_connection():
            url = 'sqlite+aiosqlite:///:memory:'

            async with create_connection(url) as app.connection:
                yield

            # The connection is automatically closed when the lifespan function returns/application is closed.

    The above example is roughly equivalent to the following code ::

        @app.lifespan
        async def start_database_connection():
            url = 'sqlite+aiosqlite:///:memory:'

            app.connection = await create_connection(url)

            yield

            await app.connection.close()

    or, if you don't want to use the lifespan method ::

        @app.event('on_shutdown')
        async def close_database_connection():
            await app.connection.close()

        async def start_database_connection():
            url = 'sqlite+aiosqlite:///:memory:'
            return await create_connection(url)

        app.connection = app.loop.run_until_complete(start_database_connection())

    Note
    -----
    This function is not recommended to use. It is better to use the
    :func:`~.create_engine` function and save the returned engine.

    Parameters
    -----------
    url: :class:`str`
        The database url.
    *args: Any
        Additional arguments.
    **kwars: Any
        Additional keyword arguments
    """
    engine = create_engine(url, *args, **kwargs)
    return engine.acquire()
    

    