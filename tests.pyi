import atom
import struct
from atom.websockets.frame import WebSocketFrame, WebSocketOpcode

app = atom.Application()
app.users = {}

@app.websocket('/ws')
async def websocket(req, websocket: atom.Websocket):
    while True:
        websocket.send_bytes(b'hello!')
        recv = await websocket.receive()
        print(DecodedCharArrayFromByteStreamIn(recv))

        # data = recv[:2]
        # head1, head2 = struct.unpack("!BB", data)

        # fin = True if head1 & 0b10000000 else False
        # rsv1 = True if head1 & 0b01000000 else False

        # rsv2 = True if head1 & 0b00100000 else False
        # rsv3 = True if head1 & 0b00010000 else False

        # opcode = WebSocketOpcode(head1 & 0b00001111)
        # print(opcode)
        # length = head2 & 0b01111111
        # print(length)

        # if length == 126:
        #     data = recv[:2]
        #     length = struct.unpack("!H", data)[0]

        # elif length == 127:
        #     data = recv[:8]
        #     length = struct.unpack("!Q", data)[0]

        # mask_bits = recv[:4]

        # data = recv[length:]
        # data = WebSocketFrame.mask(data, mask_bits)

        # frame = WebSocketFrame(
        #     opcode=opcode,
        #     fin=fin,
        #     rsv1=rsv1,
        #     rsv2=rsv2,
        #     rsv3=rsv3,
        #     data=data
        # )

        # print(frame.data)

def DecodedCharArrayFromByteStreamIn(stringStreamIn):
    #turn string values into opererable numeric byte values
    byteArray = [character for character in stringStreamIn]
    datalength = byteArray[1] & 127
    indexFirstMask = 2 
    if datalength == 126:
        indexFirstMask = 4
    elif datalength == 127:
        indexFirstMask = 10
    masks = [m for m in byteArray[indexFirstMask : indexFirstMask+4]]
    indexFirstDataByte = indexFirstMask + 4
    decodedChars = []
    i = indexFirstDataByte
    j = 0
    while i < len(byteArray):
        decodedChars.append( chr(byteArray[i] ^ masks[j % 4]) )
        i += 1
        j += 1
    return decodedChars

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080)