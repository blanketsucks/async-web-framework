from __future__ import annotations
from typing import TYPE_CHECKING, AsyncIterator, Callable, Generic, ItemsView, Optional, Union, Type, Tuple, List, Dict, Any, Mapping, Sequence

import sqlalchemy
from sqlalchemy import sql

from railway.models import Model
from .results import CursorResult, Row, TypedCursorResult
from .engine import Connection
from .sqltypes import Column
from .types import SchemaT, Bind, Entity
from .filters import SelectFilter, ColumnFilter

__all__ = (
    'MetaData',
    'SchemaMeta',
    'Schema',
    'create_schema'
)

class ConnectionContext(Generic[SchemaT]):
    connection: Connection

    def __init__(self, bind: Bind, schema: Type[SchemaT]) -> None:
        self.bind = bind
        self.schema = schema
        self.should_close = False

    async def execute(self, query: Any, *args: Any, **kwargs: Any):
        result = await self.raw_execute(query, *args, **kwargs)
        return TypedCursorResult.from_cursor_result(result, type=self.schema)

    async def raw_execute(self, *args: Any, **kwargs: Any) -> CursorResult:
        return await self.connection.execute(*args, **kwargs)

    async def run(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        await self.connection.run(fn, *args, **kwargs)

    async def __aenter__(self) -> ConnectionContext[SchemaT]:
        if isinstance(self.bind, Connection):
            self.connection = self.bind
        else:
            self.connection = await self.bind.acquire()
            self.should_close = True

        return self

    async def __aexit__(self, *args: Any) -> Any:
        await self.connection.commit()

        if self.should_close:
            await self.connection.close()
            
class MetaData:
    def __init__(self, bind: Optional[Bind]=None) -> None:
        self.wrapped = sqlalchemy.MetaData()
        self._schemas: List[Type[Schema]] = []
        self.bind = bind

    @property
    def schemas(self) -> Tuple[Type[Schema], ...]:
        return tuple(self._schemas)

    def add_table(self, schema: Type[Schema]) -> None:
        if self.bind:
            schema.query.bind = self.bind

        self._schemas.append(schema)

    def clear(self) -> None:
        self._schemas.clear()

    def update_schema_connections(self, bind: Bind) -> None:
        for schema in self._schemas:
            schema.query.bind = bind

    def set_bind(self, bind: Bind) -> None:
        self._connection = bind
        self.update_schema_connections(bind)
        
    async def create_all(self, *, bind: Optional[Bind]=None) -> None:
        if bind is not None:
            self.set_bind(bind)

        for schema in self.schemas:
            await schema.query.create_schema()

    async def drop_all(self) -> None:
        for schema in self.schemas:
            await schema.query.drop_schema()

class SchemaQuery(Generic[SchemaT]):
    def __init__(self, schema: Type[SchemaT], *, bind: Optional[Bind]=None) -> None:
        self.schema = schema
        self.bind = bind

    def context(self) -> ConnectionContext[SchemaT]:
        if self.bind is None:
            raise ValueError('A bind must be set')

        return ConnectionContext(self.bind, self.schema)

    def select(self, *args: Any) -> sql.Select:
        return self.schema.table.select(*args)

    async def execute(self, *args: Any, **kwargs: Any) -> TypedCursorResult[SchemaT]:
        async with self.context() as context:
            return await context.execute(*args, **kwargs)

    async def create_schema(self) -> None:
        async with self.context() as context:
            await context.run(self.schema.table.create, checkfirst=True)

    async def drop_schema(self) -> None:
        async with self.context() as context:
            await context.run(self.schema.table.drop, checkfirst=True)

    async def all(self) -> List[SchemaT]:
        select = self.schema.table.select()

        cursor = await self.execute(select)
        return await cursor.fetchall()

    async def first(self) -> Optional[SchemaT]:
        select = self.schema.table.select().limit(1)

        cursor = await self.execute(select)
        return await cursor.first()

    async def get(self, *conditions: Any) -> Optional[SchemaT]:
        select = self.schema.table.select().where(*conditions)

        cursor = await self.execute(select)
        return await cursor.fetchone()

    async def getall(self, *conditions: Any) -> List[SchemaT]:
        select = self.schema.table.select()
        select.where(*conditions)

        async with self.context() as context:
            cursor = await context.execute(select)
            return await cursor.fetchall()

    async def put(self, entity: Entity[SchemaT]) -> Optional[SchemaT]:
        insert = self.schema.table.insert()

        values: Union[Mapping[str, Any], Sequence[Any]]
        if isinstance(entity, Model):
            values = entity.to_dict()
        elif isinstance(entity, (Mapping, Sequence)):
            values = entity
        else:
            values = {
                column.name: getattr(entity, column.name)
                for column in entity.__columns__ if not column.primary_key
            }

        insert = insert.values(values)
        await self.execute(insert)

        primary_key = self.schema.get_primary_key()
        if primary_key is not None:
            select = self.schema.table.select().order_by(primary_key.desc()).limit(1)

            cursor = await self.execute(select)
            return await cursor.first()

        return None
        
    async def putall(self, *entities: Entity[SchemaT]) -> List[SchemaT]:
        objects = []

        for entity in entities:
            obj = await self.put(entity)
            objects.append(obj)

        if any(objects):
            return objects

        return []

    async def insert(self, *entities: Entity[SchemaT]) -> List[SchemaT]:
        return await self.putall(*entities)

    async def update(self, *where: Any, **attrs: Any) -> None:
        update = self.schema.table.update().where(*where).values(**attrs)
        async with self.context() as context:
            await context.execute(update)

    async def delete(self, *where: Any) -> None:
        delete = self.schema.table.delete().where(*where)
        async with self.context() as context:
            await context.execute(delete)
        
    def filter(self) -> SelectFilter[SchemaT]:
        return SelectFilter(self)

    def with_columns(self, *columns: Column[Any]) -> ColumnFilter[SchemaT]:
        return ColumnFilter(self, columns)

    def __aiter__(self) -> AsyncIterator[SchemaT]:
        return self.filter().__aiter__() # type: ignore

class SchemaMeta(type):
    if TYPE_CHECKING:
        def __getattr__(self, name: str) -> Column[Any]: ...
        
    __columns__: List[sqlalchemy.Column]
    __metadata__: sqlalchemy.MetaData
    __table__: sqlalchemy.Table
    __query__: SchemaQuery[Any]

    def __new__(cls, cls_name: str, bases: Tuple[Any, ...], attrs: Dict[str, Any], **kwargs: Any) -> Any:
        name = kwargs.get('name', cls_name)

        metadata = kwargs.get('metadata', MetaData())
        columns: List[sqlalchemy.Column] = []

        for attr, value in attrs.items():
            if isinstance(value, sqlalchemy.Column):
                value.name = attr
                columns.append(value)

        repr = kwargs.get('repr', False)

        attrs['__use_repr__'] = repr
        attrs['__columns__'] = columns
        attrs['__metadata__'] = metadata
        attrs['__table__'] = sqlalchemy.Table(name, metadata.wrapped, *columns)

        table = super().__new__(cls, cls_name, bases, attrs)
        table.__query__ = SchemaQuery(table) # type: ignore

        metadata.add_table(table)
        return table

    @property
    def columns(self) -> Tuple[sqlalchemy.Column[Any], ...]:
        return tuple(self.__columns__)

    @property
    def table(self) -> sqlalchemy.Table:
        return self.__table__

    @property
    def query(self: Type[SchemaT]) -> SchemaQuery[SchemaT]: # type: ignore
        return self.__query__

    @property
    def metadata(self) -> sqlalchemy.MetaData:
        return self.__metadata__

    def get_primary_key(self) -> Optional[Column[Any]]:
        primary_key = None
        if self.table.primary_key.columns:
            primary_key = self.table.primary_key.columns.values()[0]

        return primary_key

    def get_primary_keys(self) -> List[Column[Any]]:
        return self.table.primary_key.columns.values()

class Schema(metaclass=SchemaMeta):
    __use_repr__: bool
    __columns__: List[sqlalchemy.Column[Any]]

    def __init__(self, **kwargs: Any):
        self.update_attributes(**kwargs)

    def __repr__(self) -> str:
        if self.__use_repr__:
            attrs = ' '.join([f'{key}={value!r}' for key, value in self.to_dict().items()])
            return f'<{self.__class__.__name__} {attrs}>'

        return super().__repr__()

    @classmethod
    def from_row(cls: Type[SchemaT], row: Row) -> SchemaT:
        return cls(**row.as_dict())

    def to_dict(self) -> Dict[str, Any]:
        data = {}

        for column in self.__columns__:
            value = getattr(self, column.name)
            data[column.name] = value

        return data

    def items(self) -> ItemsView[str, Any]:
        return ItemsView(self.to_dict())

    def update_attributes(self, **values: Any) -> None:
        for key, value in values.items():
            if not hasattr(self, key):
                raise AttributeError(f'{key} is not a valid attribute')

            if getattr(self, key) != value:
                setattr(self, key, value)

    def get_primary_key_conditions(self) -> Tuple[Any, ...]:
        cls = type(self)
        columns = cls.get_primary_keys()

        return tuple(column == getattr(self, column.name) for column in columns)

    def get_execute_conditions(self) -> Tuple[Any, ...]:
        cls = type(self)
        if cls.get_primary_keys():
            return self.get_primary_key_conditions()

        return tuple(column == getattr(self, column.name) for column in cls.columns)

    def get_column_values(self) -> Dict[str, Any]:
        cls = type(self)
        values = {}

        for column in cls.columns:
            if column.primary_key:
                continue

            value = getattr(self, column.name)
            values[column.name] = value

        return values

    async def update(
        self,
        **attrs: Any
    ) -> None:
        cls = type(self)
        where = self.get_execute_conditions()
        
        values = self.get_column_values()
        values.update(attrs)

        await cls.query.update(*where, **attrs)
        self.update_attributes(**attrs)

    async def save(self) -> None:
        cls = type(self)
        schema = await cls.query.put(self)

        if schema is not None:
            self.update_attributes(**schema.to_dict())

    async def delete(self) -> None:
        where = self.get_execute_conditions()

        cls = type(self)
        await cls.query.delete(*where)

def create_schema(name: str, *columns: Column, metadata: Optional[MetaData]=None) -> Type[Schema]:
    namespace = {
        column.name: column for column in columns
    }

    kwargs = {}
    if metadata:
        kwargs['metadata'] = metadata

    bases = (Schema,)
    return SchemaMeta(name, bases, namespace, **kwargs) # type: ignore