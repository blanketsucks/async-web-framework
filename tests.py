from atom import websocket
from atom import server

import asyncio

async def handler(ws: websocket.Websocket):
    while True:
        print(await ws.receive())
        await ws.send('HELLO WORLD'.encode('utf-8'))


class Protocol(websocket.WebsocketProtocol):
    async def on_request(self):
        if self.path == '/feed':
            ws = await self.conn.handshake()
            await handler(ws)

async def main():
    loop = asyncio.get_event_loop()
    protocol = Protocol(loop)
    
    serv = websocket.WebsocketServer(
        protocol, '127.0.0.1', 8080, loop=protocol.loop
    )
    await serv.serve()

asyncio.run(main())
