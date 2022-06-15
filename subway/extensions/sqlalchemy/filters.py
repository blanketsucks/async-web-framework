from __future__ import annotations

from typing import List, Optional, Generic, TYPE_CHECKING, Any, Sequence
from sqlalchemy import sql, Column
from abc import ABC, abstractmethod
import asyncio

from .results import Row
from .types import SchemaT

if TYPE_CHECKING:
    from .schemas import SchemaQuery

__all__ = (
    'AbstractFilter',
    'AbstractFilterIterator',
    'SelectFilter',
    'SelectFilterIterator',
    'ColumnFilter',
    'ColumnFilterIterator',
)

class AbstractFilter(Generic[SchemaT], ABC):
    def __init__(self, query: SchemaQuery[SchemaT], *args: Any) -> None:
        self.query = query
        self.select = query.select(*args)

    async def one(self) -> Optional[SchemaT]:
        cursor = await self.query.execute(self.select)
        return await cursor.fetchone()

    async def all(self) -> List[SchemaT]:
        cursor = await self.query.execute(self.select)
        return await cursor.fetchall()

    async def many(self, *, size: Optional[int] = None) -> List[SchemaT]:
        cursor = await self.query.execute(self.select)
        return await cursor.fetchmany(size)

    @abstractmethod
    def __aiter__(self) -> Any:
        raise NotImplementedError

class AbstractFilterIterator(Generic[SchemaT], ABC):
    def __init__(self, filter: AbstractFilter[SchemaT]) -> None:
        self.filter = filter
        self.queue = asyncio.Queue[SchemaT]()
        self.filled = False

    @abstractmethod
    async def fill(self) -> None:
        raise NotImplementedError

    async def next(self):
        if not self.filled:
            await self.fill()

        return self.queue.get_nowait()

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return await self.next()
        except asyncio.QueueEmpty:
            raise StopAsyncIteration

class SelectFilterIterator(AbstractFilterIterator[SchemaT]):
    async def fill(self) -> None:
        query = self.filter.query
        select = self.filter.select

        async with query.context() as context:
            cursor = await context.execute(select)

            async for row in cursor:    
                await self.queue.put(row) # type: ignore

        self.filled = True

class SelectFilter(AbstractFilter[SchemaT]):
    def order_by(self, *args: Any):
        self.select = self.select.order_by(*args)
        return self

    def limit(self, limit: int):
        self.select = self.select.limit(limit)
        return self

    def offset(self, offset: int):
        self.select = self.select.offset(offset)
        return self

    def where(self, *conditions: Any):
        self.select = self.select.where(*conditions)
        return self

    def __aiter__(self):
        return SelectFilterIterator(self)

class ColumnFilterIterator(AbstractFilterIterator[Any]):
    if TYPE_CHECKING:
        async def __anext__(self) -> Row: ...

    async def fill(self) -> None:
        query = self.filter.query
        select = self.filter.select

        async with query.context() as context:
            cursor = await context.raw_execute(select)

            async for row in cursor:    
                await self.queue.put(row)

        self.filled = True

class ColumnFilter(SelectFilter[SchemaT], ABC):
    def __init__(self, query: SchemaQuery[SchemaT], columns: Sequence[Column[Any]]) -> None:
        self.query = query
        self.select = sql.select(columns)

    async def many(self, size: Optional[int] = None) -> List[Row]:
        async with self.query.context() as context:
            cursor = await context.raw_execute(self.select)
            return await cursor.fetchmany(size)

    async def all(self) -> List[Row]:
        query = self.query
        select = self.select

        async with query.context() as context:
            cursor = await context.raw_execute(select)
            return await cursor.fetchall()

    async def one(self) -> Optional[Row]:
        query = self.query
        select = self.select

        async with query.context() as context:
            cursor = await context.raw_execute(select)
            return await cursor.fetchone()

    def __aiter__(self) -> ColumnFilterIterator: 
        return ColumnFilterIterator(self)
