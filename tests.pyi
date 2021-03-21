import socket

with socket.create_server(('127.0.0.1', 8080)) as server:
    while True:
        client, addr = server.accept()
        client.sendall(b'Hello friend')

        data = client.recv(4096)
        print(data.decode())

        client.close()