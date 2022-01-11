from railway import Application, Request, websockets

app = Application()

@app.websocket('/echo')
async def echo(request: Request[Application], websocket: websockets.ServerWebSocket) -> None:
    async with websocket:
        async for data in websocket:
            await websocket.send(data.data)

app.run()
