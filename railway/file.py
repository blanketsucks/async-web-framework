from typing import Any, AsyncGenerator, List, Union, Optional
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

    async def stream(self) -> AsyncGenerator[bytes]:
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
