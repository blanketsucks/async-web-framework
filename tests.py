
from atom import restful
import atom

app = restful.App()

@app.websocket('/feed', 'GET', subprotocols=('wpcp',))
async def web(request: atom.Request, websocket: atom.WebsocketProtocolConnection):
    data = 'hello!'
    print('Sending: ' + data)
    print('Closing...')
    await websocket.close()

@app.route('/', 'GET')
async def index(req):
    return ''

print(app.routes)

if __name__ == '__main__':
    # asyncio.run raises an error here, idk why
    app.loop.run_until_complete(app.start())