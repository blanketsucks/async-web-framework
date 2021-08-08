import aiohttp
import asyncio

async def get(tries):
    try:
        print(f'Try: {tries}')

        connector = aiohttp.TCPConnector()
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get('http://127.0.0.1:8080/post') as resp:
                pass
    except Exception as e:
        raise e

async def main():
    tasks = [get(i) for i in range(100)]
    await asyncio.gather(*tasks, return_exceptions=True)

asyncio.run(main())