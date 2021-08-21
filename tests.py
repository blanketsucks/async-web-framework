import asyncio
import atom

app = atom.Application()

from atom.openapi.router import openapi
app.add_router(openapi)

asyncio.run(atom.run(app))