from atom.server import sockets

async def main():
    async with sockets.create_server('127.0.0.1', 8080) as socket:
        while True:
            client = await socket.accept()
            await client.send(b'Hello there!')

            client.close()

import asyncio
loop = asyncio.get_event_loop()
loop.run_until_complete(main())