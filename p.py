import asyncio
import atom

app = atom.Application(host="::1", ipv6=True)
print(app.socket.getsockname())
asyncio.run(atom.run(app))