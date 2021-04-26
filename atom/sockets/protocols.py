
from .transports import Transport, WebsocketTransport
from .frame import Data

class Protocol:
    
    async def on_connection_made(self, transport: Transport):
        ...

    async def on_connection_lost(self):
        ...

    async def on_data_receive(self, data: bytes):
        ...

class WebsocketProtocol(Protocol):

    async def on_connection_made(self, transport: WebsocketTransport):
        ...

    async def on_websocket_data(self, data: Data):
        ...
