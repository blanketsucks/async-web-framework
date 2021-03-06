
import socket
import asyncio
import concurrent.futures

MAGIC = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

__all__ = (
    'MAGIC',
    'Websocket'
)

class Websocket:
    def __init__(self, __socket: socket.socket, __loop: asyncio.AbstractEventLoop) -> None:

        self.__pool = concurrent.futures.ThreadPoolExecutor(max_workers=10)
        self.__socket = __socket
        self.__loop = __loop

    def _decode_frame(self, frame):
        payload_len = frame[1] - 128

        mask = frame [2:6]
        encrypted_payload = frame [6: 6 + payload_len]

        payload = bytearray([encrypted_payload[i] ^ mask[i%4] for i in range(payload_len)])
        return payload

    async def _send_frame(self, payload):
        frame = [129]
        frame += [len(payload)]

        frame_to_send = bytearray(frame) + payload
        return await self.__loop.sock_sendall(
            sock=self.__socket,
            data=frame_to_send
        )

    async def send(self, data: bytes):
        return await self._send_frame(
            payload=data
        )

    async def receive(self):
        data = await self.__loop.sock_recv(self.__socket, 1024)
        payload = bytearray(data.strip())
        
        with self.__pool as pool:
            result = await self.__loop.run_in_executor(
                pool, self._decode_frame(payload)
            )

            return result

