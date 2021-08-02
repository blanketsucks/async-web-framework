import asyncio
import aiohttp

async def main():
    async with aiohttp.ClientSession() as session:
        async with session.get('http://127.0.0.1:8080/download/test') as resp:
            resp.raise_for_status()
            file = await resp.read()
            
            with open('pog.py', 'wb') as f:
                f.write(file)

asyncio.run(main())