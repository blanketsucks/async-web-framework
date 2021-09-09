"""
MIT License

Copyright (c) 2021 blanketsucks

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
from typing import Any, AsyncIterator, List, Union, Optional
import pathlib
import io

from . import compat

__all__ = (
    'File',
)

class File:
    fp: io.TextIOWrapper
    """
    Attributes:
        filename: The name of the file.
        fp: The file object.
    """
    def __init__(self, fp: Union[str, pathlib.Path, io.BytesIO], *, filename: Optional[str]=None) -> None:
        """
        File constructor.

        Args:
            fp: Can be either `str`, `pathlib.Path` or an `io.BytesIO` object.
            filename: The name of the file.
        """

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

        self.filename: Optional[str] = filename
    
    async def __aenter__(self):
        return self

    async def __aexit__(self, *args: Any):
        await self.close()

    def __aiter__(self):
        return self.stream()

    async def save_as(self, name: str):
        """
        Saves the file as `name`.

        Args:
            name: The name of the file.
        """
        loop = compat.get_running_loop()
        data = await self.read()

        def save(fn: str, data: bytes):
            with open(fn, 'wb') as f:
                f.write(data)

        await loop.run_in_executor(None, save, name, data)

    async def read(self) -> bytes:
        """
        Reads the file.

        Returns:
            The file data.
        """
        loop = compat.get_running_loop()
        data = await loop.run_in_executor(None, self.fp.read)

        return data

    async def readlines(self) -> List[bytes]:
        """
        Reads the file as a list of lines.

        Returns:
            list of bytes.
        
        """
        loop = compat.get_running_loop()
        data = await loop.run_in_executor(None, self.fp.readlines)

        return data

    async def stream(self) -> AsyncIterator[bytes]:
        """
        An async generator that reads the file.

        Returns:
            An async generator that yields the file data.
        """
        lines = await self.readlines()
        
        for line in lines:
            yield line

    async def close(self):
        """
        Closes the file
        """
        loop = compat.get_running_loop()
        await loop.run_in_executor(None, self.fp.close())
