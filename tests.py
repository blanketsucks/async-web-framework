from inspect import formatannotation
import test

@test.respect()
async def foo(bar: int) -> str: return 1233

import asyncio

asyncio.run(foo(123))