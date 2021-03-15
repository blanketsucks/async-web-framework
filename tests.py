import websockets
import asyncio

async def main():
    async with websockets.connect('ws://127.0.0.1:8080') as websocket:
        while True:
            await websocket.send('Hello')
            data = await websocket.recv()
            print(data)

asyncio.run(main())