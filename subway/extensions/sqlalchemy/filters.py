from __future__ import annotations

from sqlalchemy import sql, Column
from typing import List, Optional, Generic, TYPE_CHECKING, Any, Protocol, Sequence
import asyncio

from .results import Row
from .types import SchemaT

if TYPE_CHECKING:
    from .schemas import SchemaQuery

class Filter(Generic[SchemaT], Protocol):
    query: SchemaQuery[SchemaT]
    select: sql.Select

class FilterIterator(Generic[SchemaT]):
    def __init__(self, filter: Filter[SchemaT]) -> None:
        self.filter = filter
        self.queue = asyncio.Queue[SchemaT]()
        self.filled = False

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

class SelectFilterIterator(FilterIterator[SchemaT]):
    async def fill(self) -> None:
        query = self.filter.query
        select = self.filter.select

        async with query.context() as context:
            cursor = await context.execute(select)

            async for row in cursor:    
                await self.queue.put(row) # type: ignore

        self.filled = True

class SelectFilter(Generic[SchemaT]):
    def __init__(self, query: SchemaQuery[SchemaT]) -> None:
        self.query = query
        self.select = query.select()

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

class ColumnFilterIterator(FilterIterator):
    if TYPE_CHECKING:
        async def __anext__(self) -> Row: ...

    async def fill(self) -> None:
        query = self.filter.query
        select = self.filter.select

        async with query.context() as context:
            cursor = await context.raw_execute(select)

            async for row in cursor:    
                await self.queue.put(row) # type: ignore

        self.filled = True

class ColumnFilter(SelectFilter[SchemaT]):
    def __init__(self, query: SchemaQuery[SchemaT], columns: Sequence[Column[Any]]) -> None:
        self.query = query
        self.select = sql.select(columns)

    async def fetchmany(self, size: Optional[int]=None) -> List[Row]:
        async with self.query.context() as context:
            cursor = await context.raw_execute(self.select)
            return await cursor.fetchmany(size)

    async def all(self) -> List[Row]:
        query = self.query
        select = self.select

        async with query.context() as context:
            cursor = await context.raw_execute(select)
            return await cursor.fetchall()

    async def fetchone(self) -> Optional[Row]:
        query = self.query
        select = self.select

        async with query.context() as context:
            cursor = await context.raw_execute(select)
            return await cursor.fetchone()

    def __aiter__(self) -> ColumnFilterIterator: 
        return ColumnFilterIterator(self)
