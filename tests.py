from railway import ipc

client = ipc.IPCClient('127.0.0.1', 5000, 'secretkey')
        
client.loop.run_until_complete(client.connect())