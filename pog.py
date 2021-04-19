from atom.sockets import sessions
import aiohttp

session = sessions.Session()

async def main():
    data = await session.request('', 'GET')
    print(data.body)

session._loop.run_until_complete(main())

