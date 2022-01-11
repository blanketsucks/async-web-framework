from __future__ import annotations

from typing import IO, Any, Iterable, List, Union, Optional
import io

from .types import BytesLike, OpenFile
from . import compat

_open = open

class FileContextManager:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.args = args
        self.kwargs = kwargs

    async def open(self) -> File:
        fd = await compat.run_in_thread(_open, *self.args, **self.kwargs)
        return File(fd) # type: ignore

    def __await__(self):
        return self.open().__await__()

    async def __aenter__(self) -> File:
        self.file = await self.open()
        return self.file

    async def __aexit__(self, *args: Any) -> None:
        await self.file.close()


def open(file: OpenFile, mode: Optional[str] = None, **kwargs: Any):
    """
    Open a file in a binary mode.

    Parameters
    ----------
    file: Union[:class:`str`, :class:`bytes`, :class:`int`, :class:`os.PathLike`]
        A path to a file or a file descriptor.
    mode: Optional[:class:`str`]
        The mode to open the file in. Defaults to 'rb'.
    **kwargs: Any
        Extra keyword arguments to pass into :func:`open`

    Returns
    -------
    An awaitable and a context manager that return a :class:`~.File` instance.
    """
    if mode is not None:
        if 'b' not in mode:
            mode += 'b'
    else:
        mode = 'rb'

    return FileContextManager(file, mode, **kwargs)


__all__ = (
    'File',
    'open'
)


class File:
    """
    Parameters
    ----------
    source: Union[:class:`io.BytesIO`, :class:`bytes`, :class:`bytearray`, :class:`memoryview`]
        An instance of :class:`io.BytesIO` or a bytes-like object.
    filename: Optional[:class:`str`]
        An optional file name.

    Attributes
    -----------
    filename: :class:`str`
        The name of the file.
    fp: :class:`io.BufferedIOBase`
        The file object.
    """
    def __init__(self, source: Union[io.BytesIO, BytesLike, IO[bytes]], *, filename: Optional[str] = None) -> None:
        if isinstance(source, (bytes, bytearray, memoryview)):
            source = io.BytesIO(source)

        self.fp = source
        self.filename: Any = getattr(self.fp, 'name', filename)

    def __repr__(self) -> str:
        return f'<File filename={self.filename!r}>'

    def __del__(self) -> None:
        if not self.closed:
            self.fp.close()
    
    async def __aenter__(self):
        return self

    async def __aexit__(self, *args: Any):
        await self.close()

    async def run_in_thread(self, name: str, *args: Any, **kwargs: Any) -> Any:
        """
        Gets a method from the file's underlying file object and runs it in a thread.

        Parameters
        ----------
        name: :class:`str`
            The name of the method to get.
        *args: Any
            The arguments to pass into the method.
        **kwargs: Any
        """
        func = getattr(self.fp, name)
        return await compat.run_in_thread(func, *args, **kwargs)

    @classmethod
    def from_file(cls, file: File):
        """
        Creates a new file from an existing file.

        Parameters
        ----------
        file: :class:`~.File`
            The file to create a new file from.
        """
        return cls(file.fp, filename=file.filename)

    @property
    def closed(self) -> bool:
        """
        Returns whether the file is closed.
        """
        return self.fp.closed

    @property
    def mode(self) -> str:
        """
        Returns the mode of the file.
        """
        mode = getattr(self.fp, 'mode', None)
        if not mode:
            if self.writable() and self.readable():
                mode = 'w+b'
            elif self.writable():
                mode = 'wb'
            elif self.readable():
                mode = 'rb'
            else:
                raise RuntimeError('Unknown file mode')

        return mode
            
    @property
    def raw(self) -> Optional[IO[bytes]]:
        """
        Returns the raw file object.
        """
        return getattr(self.fp, 'raw', None)

    async def seek(self, offset: int, whence: Optional[int] = None):
        """
        Seeks to the given offset.

        Parameters
        ----------
        offset: :class:`int`
            The offset to seek to.
        whence: Optional[:class:`int`]
            The position to seek from.
        """
        if whence is not None:
            return await compat.run_in_thread(self.fp.seek, offset, whence)
        else:
            return await compat.run_in_thread(self.fp.seek, offset)

    async def save(self, name: Optional[str] = None):
        """
        Saves the file as ``name``.

        Parameters
        ----------
        name: :class:`str`
            The name of the file.
        """
        if name is None:
            name = self.filename

        assert name is not None, 'No filename specified'
        data = await self.read()

        async with open(name, 'wb') as file:
            return await file.write(data)

    async def read(self, n: Optional[int] = None) -> bytes:
        """
        Reads the file.

        Parameters
        ----------
        n: Optional[:class:`int`]
            The number of bytes to read.
        """
        return await self.run_in_thread('read', n)

    async def readlines(self, hint: Optional[int] = None) -> List[bytes]:
        """
        Reads the file as a list of lines. 

        Parameters
        ----------
        hint: Optional[:class:`int`]
            The hint to use for the number of lines.
        """
        return await self.run_in_thread('readlines', hint)

    async def write(self, data: BytesLike):
        """
        Writes data to the file.

        Parameters
        ----------
        data: :class:`bytes`
            The data to write.
        """
        return await self.run_in_thread('write', data)

    async def writelines(self, data: Iterable[BytesLike]):
        """
        Writes a list of lines to the file.

        Parameters
        ----------
        data: List[:class:`bytes`]
            The data to write.
        """
        return await self.run_in_thread('writelines', data)

    async def truncate(self, size: Optional[int] = None) -> int:
        """
        Truncates the file.

        Parameters
        ----------
        size: Optional[:class:`int`]
            The size to truncate the file to.
        """
        return await self.run_in_thread('truncate', size)

    async def flush(self) -> None:
        return await self.run_in_thread('flush')

    def writable(self):
        """
        Returns whether the file is writable.
        """
        return self.fp.writable()

    def readable(self):
        """
        Returns whether the file is readable.
        """
        return self.fp.readable()

    def seekable(self):
        """
        Returns whether the file is seekable.
        """
        return self.fp.seekable()

    def tell(self):
        """
        Returns the current position of the file.
        """
        return self.fp.tell()

    def fileno(self) -> int:
        """
        Returns the file descriptor.
        """
        return self.fp.fileno()

    def isatty(self) -> bool:
        """
        Returns whether the file is a tty.
        """
        return self.fp.isatty()

    async def close(self):
        """
        Closes the file
        """
        if not self.closed:
            await self.run_in_thread('close')

    def __aiter__(self):
        return self

    async def __anext__(self):
        line = await self.readlines(hint=1)
        if not line:
            raise StopAsyncIteration

        return line[0]
