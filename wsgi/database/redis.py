import aioredis

from .errors import NoConnections
from .base import BaseConnection

class RedisCluster:
    def __init__(self, connection: aioredis.Redis) -> None:
        self.connection = connection

    async def add_slots(self, slot, *slots):
        res = await self.connection.cluster_add_slots(slot, *slots)
        return res

    async def delete_slots(self, slot, *slots):
        res = await self.connection.cluster_del_slots(slot, *slots)
        return res

    def slots(self):
        res = self.connection.cluster_slots()
        self.connection.cluster
        return res

    def nodes(self):
        res = self.connection.cluster_nodes()
        return res

    def count_failure_reports(self, node_id):
        res = self.connection.cluster_count_failure_reports(node_id)
        return res

    async def replicate(self, node_id):
        res = await self.connection.cluster_replicate(node_id)
        return res

    async def forget(self, node_id):
        res = await self.connection.cluster_forget(node_id)
        return res

    async def reset(self, hard=False):
        res = await self.connection.cluster_reset(hard=hard)
        return res

    def new(self, ip, port):
        res = self.connection.cluster_meet(ip, port)
        return res

class RedisConnection(BaseConnection):

    async def connect(self, address, *, db=None, password=None, **kwargs):
        connection = await aioredis.create_redis_pool(address, db=db, password=password, loop=self.loop, **kwargs)
        
        if self.app:
            await self.app.dispatch('on_database_connect', connection)

        self._connection = connection
        self.cluster = RedisCluster(connection)

        return self._connection

    async def get(self, key, *, encoding='utf-8'):
        result = await self._connection.get(key, encoding=encoding)
        return result

    async def set(self, key, value, **kwargs):
        result = await self._connection.set(key, value, **kwargs)
        return result

    async def set_name(self, name):
        res = await self._connection.client_setname(name)
        return res

    async def get_name(self, encoding='utf-8'):
        res = await self._connection.client_getname(encoding)
        return res

    async def list(self):
        res = await self._connection.client_list()
        return res

    def kill(self):
        res = self._connection.client_kill()
        return res
    
    async def close(self):
        if not self._connection:
            raise NoConnections('No connections has been made.')

        self._connection.close()
        await self._connection.wait_closed()
