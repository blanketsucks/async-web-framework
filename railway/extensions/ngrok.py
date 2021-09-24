import asyncio
import pathlib
import logging
from typing import Union, Optional

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
    def __init__(self, ngrok: Union[str, pathlib.Path], *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not isinstance(ngrok, (str, pathlib.Path)):
            raise TypeError('ngrok argument must be a str or pathlib.Path')

        self.ngrok = str(ngrok)
        self._process = None

    @property
    def process(self) -> Optional[asyncio.subprocess.Process]:
        """
        The ngrok process.
        """
        return self._process

    async def run_ngrok_executable(self):
        """
        Runs the ngrok executable and waits.
        """
        command = [self.ngrok, 'http', str(self.port)]
        self._process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        await self._process.wait()

    def start(self) -> None:
        self.loop.create_task(
            coro=self.run_ngrok_executable(),
            name='ngrok'
        )

        log.info('Started ngrok. Check http://127.0.0.1:4040 for more info.')
        super().start()

    async def close(self) -> None:
        self.process.terminate()
        return await super().close()
