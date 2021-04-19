from atom import sockets
import fcntl

socket = sockets.socket()
conn = sockets.WebsocketConnection(socket)

conn.close()