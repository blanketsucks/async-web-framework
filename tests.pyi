import atom
import struct
from atom.websockets.frame import WebSocketFrame, WebSocketOpcode

app = atom.Application()
app.users = {}

@app.websocket('/ws')
async def websocket(req, websocket: atom.Websocket):
    while True:
        websocket.send_bytes(b'hello!')
        data, opcode = await websocket.receive()
        print(opcode, data.data)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080)