from atom import websocket
import asyncio

async def handler(ws: websocket.Websocket):
    while True:
        recv = await ws.receive()
        print(recv)

        msg = 'Hello, World!'
        await ws.send(msg.encode('utf-8'))

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
