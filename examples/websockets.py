from subway import Application, Request, websockets

app = Application()

@app.websocket('/echo')
async def echo(request: Request[Application], websocket: websockets.ServerWebSocket) -> None:
    async with websocket: # Auto-closes the websocket when done
        async for data in websocket: # Receives data from the websocket until a close frame is received
            await websocket.send(data.data)

app.run()
