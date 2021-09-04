import socket

addrs = socket.getaddrinfo(socket.gethostname(), 8080, type=socket.SOCK_STREAM)
print(addrs)