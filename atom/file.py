import asyncio
from typing import Union
import pathlib
import io

class File:
    def __init__(self, fp: Union[str, pathlib.Path, io.BytesIO], *, filename: str=None) -> None:
        if isinstance(fp, io.BytesIO):
            self.fp = fp

        if isinstance(fp, pathlib.Path):
            if not filename:
                filename = fp.name

            self.fp = fp.open('rb')

        if isinstance(fp, str):
            if not filename:
                filename = fp

            self.fp = open(fp, 'rb')

        self.filename = filename

    async def save_as(self, name: str):
        loop = asyncio.get_running_loop()
        data = await self.read()

        def save(fn: str, data: bytes):
            with open(fn, 'wb') as f:
                f.write(data)

        await loop.run_in_executor(None, save, name, data)

    async def read(self):
        loop = asyncio.get_running_loop()
        data = await loop.run_in_executor(None, self.fp.read)

        return data

    def close(self):
        self.fp.close()