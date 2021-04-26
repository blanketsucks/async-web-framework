import asyncio
import websockets

async def main():
    ws = await websockets.connect('ws://127.0.0.1:8080')
    data = await ws.recv()
    print(data)

    await ws.send('Hello')

asyncio.run(main())