from typing import Any, Union, Optional
import asyncio
import os
import logging

from railway import app

__all__ = (
    'Application',
)

log = logging.getLogger(__name__)


class Application(app.Application):
    """
    A :class:`~railway.Application` subclass that runs a local ngrok tunnel.

    Parameters
    -----------
    ngrok: Union[:class:`str`, :class:`pathlib.Path`]
        The path to the ngrok executable.
    *args:
        The positional arguments to pass to the :class:`~railway.Application`.
    **kwargs:
        The keyword arguments to pass to the :class:`~railway.Application`.

    Example
    ---------
    .. code-block:: python3

        from railway.extensions import ngrok

        app = ngrok.Application(ngrok='path/to/ngrok.exe')
        app.run()
        # Now if you open http://127.0.0.1:4040 in your browser, you'll see
        # your HTTPS and HTTP tunnels.
 
    """
    def __init__(self, ngrok: Union[str, os.PathLike[str]], *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        if not isinstance(ngrok, (str, os.PathLike)):
            raise TypeError('ngrok argument must be a path-like object or a string.')

        self.ngrok = str(ngrok)
        self._process: Optional[asyncio.subprocess.Process] = None

    @property
    def process(self) -> Optional[asyncio.subprocess.Process]:
        """
        The ngrok process.
        """
        return self._process

    async def run_ngrok_executable(self) -> None:
        """
        Runs the ngrok executable and waits.
        """
        command = [self.ngrok, 'http', str(self.port)]
        self._process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

    async def start(self) -> None:
        await self.run_ngrok_executable()

        log.info('Started ngrok. Check http://127.0.0.1:4040 for more info.')
        await super().start()

    async def close(self) -> None:
        if self.process:
            try:
                self.process.terminate()
                await self.process.wait()
            except ProcessLookupError:
                pass

            log.info('Terminated ngrok process.')

        return await super().close()
