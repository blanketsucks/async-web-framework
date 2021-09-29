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
    """
    Parameters
    ----------
    fp: Union[:class:`str`, :class:`pathlib.Path`, :class:`io.BytesIO`, :class:`bytes`, :class:`bytearray`, :class:`memoryview`]
        The path to the file. You can also pass in an instance of :class:`io.BytesIO` into this or a bytes-like object.
    filename: Optional[:class:`str`]
        An optional file name.

    Attributes
    -----------
    filename: :class:`str`
        The name of the file.
    fd: :class:`io.BufferedReader`
        The file object.
    """
    def __init__(self, fp: Union[str, pathlib.Path, io.BytesIO, bytes, bytearray, memoryview], *, filename: Optional[str]=None) -> None:
        if isinstance(fp, (bytes, bytearray, memoryview)):
            fp = io.BytesIO(fp)

        if isinstance(fp, io.BytesIO):
            self.fd = fp

        if isinstance(fp, pathlib.Path):
            if not filename:
                filename = fp.name

            self.fd = fp.open('rb')

        if isinstance(fp, str):
            if not filename:
                filename = fp

            self.fd = open(fp, 'rb')

        self.filename: Optional[str] = filename

    def __repr__(self) -> str:
        return f'<File filename={self.filename!r}>'
    
    async def __aenter__(self):
        return self

    async def __aexit__(self, *args: Any):
        await self.close()

    def __aiter__(self):
        return self.stream()

    def seek(self):
        """
        Seeks to the beginning of the file.
        """
        self.fd.seek(0)

    async def save(self, name: str):
        """
        Saves the file as ``name``.

        Parameters
        ----------
        name: :class:`str`
            The name of the file.
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
        """
        loop = compat.get_running_loop()
        data = await loop.run_in_executor(None, self.fd.read)

        self.seek()
        return data

    async def readlines(self) -> List[bytes]:
        """
        Reads the file as a list of lines. 
        """
        loop = compat.get_running_loop()
        data = await loop.run_in_executor(None, self.fd.readlines)

        self.seek()
        return data

    async def stream(self) -> AsyncIterator[bytes]:
        """
        An async generator that reads the file.
        """
        lines = await self.readlines()
        
        for line in lines:
            yield line

    async def close(self):
        """
        Closes the file
        """
        loop = compat.get_running_loop()
        await loop.run_in_executor(None, self.fd.close)
