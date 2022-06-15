from __future__ import annotations

from typing import (
    AsyncIterator,
    Dict,
    Iterator, 
    ItemsView, 
    KeysView, 
    Optional, 
    List, 
    Any, 
    Type,
    Union, 
    Generic, 
    ValuesView, 
    overload
)
import sqlalchemy
import sqlalchemy.exc
from sqlalchemy.engine.cursor import ResultProxy as Result
from sqlalchemy.engine.row import RowProxy as _RowProxy
from sqlalchemy.ext.asyncio import AsyncResult

from .types import ResultT, FrozenResult, MappingResult, ScalarsResult
from subway.utils import copy_docstring

__all__ = (
    'Row',
    'CursorResult',
    'TypedCursorResult'
)

class RowProxy(_RowProxy):
    _mapping: Dict[str, Any]
    def _asdict(self) -> Dict[str, Any]: ...

class Row:
    """
    A wrapped around the :class:`sqlalchemy.engine.RowProxy` class.
    Provides a dictionary-like interface to the row.

    Note
    ------
    This class is not intended to be instantiated directly.

    Attributes
    ----------
    proxy: :class:`sqlalchemy.engine.RowProxy`
        The wrapped row proxy.
    """
    def __init__(self, proxy: RowProxy) -> None:
        self.proxy = proxy

    def __repr__(self) -> str:
        return repr(self.proxy)

    def keys(self) -> KeysView[str]:
        """
        Return a view of keys for string column names represented in the row.
        """
        return self.proxy._mapping.keys()

    def values(self) -> ValuesView[Any]:
        """
        Return a view of values for the values represented in the row.
        """
        return self.proxy._mapping.values()

    def items(self) -> ItemsView[str, Any]:
        """
        Return a view of key/value tuples for the elements in the row.
        """
        items = self.proxy._asdict()
        return ItemsView(items)

    def as_dict(self) -> Dict[str, Any]:
        """
        Returns the row as a dictionary.
        """
        return self.proxy._asdict()

    def __getitem__(self, key: Union[str, int]) -> Any:
        """
        Allows the row to be accessed as a dictionary or a sequence.

        Parameters
        ----------
        key: Union[:class:`str`, :class:`int`]
            The key to access the row by. If the key is a string, the value
            is gotten from the row dictionary. If the key is an integer, the
            value is gotten from the row sequence.
        """
        if isinstance(key, int):
            return self.proxy[key]

        return self.proxy._mapping[key]

    def __iter__(self) -> Iterator[Any]:
        """
        Returns an iterator over the row elements.
        """
        return iter(self.proxy)

class CursorResult:
    """
    Wraps around the :class:`sqlalchemy.ext.asyncio.AsyncResult` class.
    """
    def __init__(self, result: Result) -> None:
        self.wrapped = AsyncResult(result)
        self.original = result

    def __aiter__(self) -> CursorResult:
        """
        Returns an iterator over the :class:`~.Row`s in the result.
        """
        return self

    async def __anext__(self) -> Row:
        try:
            row = await self.fetchone()
            if row is None:
                raise StopAsyncIteration

            return row
        except sqlalchemy.exc.ResourceClosedError:
            raise StopAsyncIteration

    async def __aenter__(self) -> CursorResult:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()    

    def keys(self) -> KeysView[str]:
        return self.wrapped.keys()

    def mapping(self) -> MappingResult:
        """
        Returns
        ---------
        :class:`sqlalchemy.ext.asyncio.`
        """
        return self.wrapped.mappings() # type: ignore

    def scalars(self, index: int = 0) -> ScalarsResult:
        return self.wrapped.scalars(index) # type: ignore

    async def fetchone(self) -> Optional[Row]:
        """
        Fetch the next row from the result.
        """
        row = await self.wrapped.fetchone()
        if row is not None:
            return Row(row)

    async def fetchmany(self, size: Optional[int] = None) -> List[Row]:
        """
        Fetch the next set of rows from the result.

        Parameters
        ----------
        size: Optional[:class:`int`]
            The number of rows to fetch.
        """
        rows = await self.wrapped.fetchmany(size)
        return [Row(row) for row in rows]

    async def fetchall(self) -> List[Row]:
        """
        Fetch all rows from the result.
        """
        rows = await self.wrapped.all()
        return [Row(row) for row in rows]

    async def all(self) -> List[Row]:
        """
        An alias for :meth:`~.fetchall`.
        """
        rows = await self.wrapped.all()
        return [Row(row) for row in rows]

    async def scalar(self) -> Optional[Row]:
        row = await self.wrapped.scalar()
        if row is not None:
            return Row(row)

    async def first(self) -> Optional[Row]:
        """
        Return the first row from the result.
        """
        row = await self.wrapped.first()
        if row is not None:
            return Row(row)

    async def freeze(self) -> FrozenResult:
        """
        Returns
        -------
        :class:`sqlalchemy.engine.FrozenResult`
            A callable object that will produce copies of :class:`sqlalchemy.ext.asyncio.AsyncResult` when invoked.
        """
        return await self.wrapped.freeze()

    async def close(self) -> None:
        """
        Close the result.
        """
        await self.wrapped.close()

    async def partitions(self, size: Optional[int] = None) -> AsyncIterator[List[Row]]:
        """
        Returns an iterator over the result partitions.

        Parameters
        ----------
        size: Optional[:class:`int`]
            The number of rows to fetch per partition.
        """
        async for rows in self.wrapped.partitions(size): # type: ignore
            yield [Row(row) for row in rows]

class TypedCursorResult(Generic[ResultT], CursorResult):
    """
    Wraps around the :class:`sqlalchemy.ext.asyncio.AsyncResult` class.
    
    Parameters
    ----------
    result: :class:`sqlalchemy.engine.Result`
        The result to wrap.
    type: :class:`type`
        The type to cast results to. The type passed in must have a `from_row` method which takes in a single parameter which is a :class:`~.Row` object.
    """
    def __init__(self, result: Result, *, type: Type[ResultT]) -> None:
        super().__init__(result)
        self.type = type

    @classmethod
    def from_cursor_result(cls, result: CursorResult, *, type: Type[ResultT]) -> TypedCursorResult[ResultT]:
        """
        Builds a typed result from a cursor result.

        Parameters
        ----------
        result: :class:`~.CursorResult`
            The cursor result to wrap.
        type: :class:`type`
            The type to cast results to.
        """
        return cls(result.original, type=type)

    @overload
    def convert(self, row: Row) -> ResultT: ...
    @overload
    def convert(self, row: List[Row]) -> List[ResultT]: ...
    @overload
    def convert(self, row: Optional[Row]) -> Optional[ResultT]: ...
    def convert(self, row: Union[Optional[Row], List[Row]]) -> Any:
        """
        Converts a row or a list of rows to the type specified in the constructor.

        Parameters
        ----------
        row: Union[:class:`~.Row`, List[:class:`~.Row`]]
            The row to convert.
        """
        if isinstance(row, list):
            return [self.convert(r) for r in row]

        if row is None:
            return None

        return self.type.from_row(row) # type: ignore

    @copy_docstring(CursorResult.fetchone)
    async def fetchone(self) -> Optional[ResultT]:
        row = await super().fetchone()
        return self.convert(row)

    @copy_docstring(CursorResult.fetchmany)
    async def fetchmany(self, size: Optional[int] = None) -> List[ResultT]:
        rows = await super().fetchmany(size)
        return self.convert(rows)

    @copy_docstring(CursorResult.fetchall)
    async def fetchall(self) -> List[ResultT]:
        rows = await super().fetchall()
        return self.convert(rows)

    @copy_docstring(CursorResult.all)
    async def all(self) -> List[ResultT]:
        rows = await super().all()
        return self.convert(rows)

    @copy_docstring(CursorResult.scalar)
    async def scalar(self) -> Optional[ResultT]:
        row = await super().scalar()
        return self.convert(row)

    @copy_docstring(CursorResult.first)
    async def first(self) -> Optional[ResultT]:
        row = await super().first()
        return self.convert(row)

    @copy_docstring(CursorResult.partitions)
    async def partitions(self, size: Optional[int] = None) -> AsyncIterator[List[ResultT]]:
        async for rows in super().partitions(size=size):
            yield self.convert(rows)

    async def __anext__(self) -> ResultT:
        try:
            row = await self.fetchone()
            if row is None:
                raise StopAsyncIteration

            return row
        except sqlalchemy.exc.ResourceClosedError:
            raise StopAsyncIteration