import socket

addrs = socket.getaddrinfo(socket.gethostname(), None, type=socket.SOCK_STREAM)
print(addrs)