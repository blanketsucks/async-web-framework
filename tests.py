
from atom import restful
import atom

app = restful.App()
app._is_websocket = True

@app.websocket('/feed', 'GET', subprotocols='wpcp,')
async def web(request: atom.Request, websocket: atom.WebsocketProtocolConnection):
    print('Dispatched WS.')
    while True:
        data = 'hello!'
        print('Sending: ' + data)
        await websocket.send(data)
        data = await websocket.recv()
        print('Received: ' + data)

print(app.routes)

if __name__ == '__main__':
    app.run()