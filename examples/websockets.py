from subway import Application, Request, WebSocketHTTPView, websockets

app = Application()

@app.websocket('/echo')
async def echo(request: Request[Application], websocket: websockets.WebSocket) -> None:
    async with websocket: # Auto-closes the websocket when done
        async for data in websocket: # Receives data from the websocket until a close frame is received
            await websocket.send(data.data)

# Or, as a WebSocket view

class Echo(WebSocketHTTPView, path='/echo'):

    async def on_receive(self, websocket: websockets.WebSocket, data: websockets.Data):
        await websocket.send(data.data)

app.add_websocket_view(Echo)

app.run()
