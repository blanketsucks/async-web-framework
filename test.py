import asyncio
import websockets

async def main():
    async with websockets.connect('ws://127.0.0.1:8080/ws') as ws:
        while True:
            data = await ws.recv()
            print(data)

            await ws.send('hello back')
            await asyncio.sleep(2)

asyncio.run(main())