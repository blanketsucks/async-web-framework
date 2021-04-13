
from atom.server.sockets.sockets import socket
from io import open_code
from atom.server import sockets
import asyncio
import zlib

zlib.decompress()

loop = asyncio.get_event_loop()

class Protocol:
    def dispatch(self, name: str, *args, loop=None):
        if not loop:
            loop = asyncio.get_event_loop()

        method = getattr(self, 'on_'+name, None)
        if not method:
            return

        return loop.create_task(method(*args))

    async def on_websocket_connect(self, websocket: sockets.Websocket):
        self.ws = websocket
        print('Connected!')

    async def on_websocket_receive(self, data: sockets.Data):

        print(data.raw, data.data, data.frame)
        await self.ws.send_str('Hello, World!')

async def keep_alive(ws: sockets.Websocket):
    while not ws.state is sockets.WebSocketState.CLOSED:
        await ws.ping()
        await asyncio.sleep(10)

async def main():
    ws = sockets.Websocket()
    proto = Protocol()

    await ws.connect('echo.websocket.org', '/', 80)
    proto.dispatch('websocket_connect', ws)

    task = ws._loop.create_task(
        keep_alive(ws)
    )

    while True:
        data, opcode = await ws.receive()
        proto.dispatch('websocket_receive', data)

        await asyncio.sleep(2)

loop.run_until_complete(main())