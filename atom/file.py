from typing import Any, Union, Optional
import pathlib
import io

from . import compat

__all__ = (
    'File',
)

class File:
    def __init__(self, fp: Union[str, pathlib.Path, io.BytesIO], *, filename: Optional[str]=None) -> None:
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
    
    async def __aenter__(self):
        return self

    async def __aexit__(self, *args: Any):
        await self.close()

    def __aiter__(self):
        return self.stream()

    async def save_as(self, name: str):
        loop = compat.get_running_loop()
        data = await self.read()

        def save(fn: str, data: bytes):
            with open(fn, 'wb') as f:
                f.write(data)

        await loop.run_in_executor(None, save, name, data)

    async def read(self):
        loop = compat.get_running_loop()
        data = await loop.run_in_executor(None, self.fp.read)

        return data

    async def readlines(self):
        loop = compat.get_running_loop()
        data = await loop.run_in_executor(None, self.fp.readlines)

        return data

    async def stream(self):
        lines = await self.readlines()
        
        for line in lines:
            yield line

    async def close(self):
        loop = compat.get_running_loop()
        await loop.run_in_executor(None, self.fp.close())
