import asyncio
from typing import Union, Optional
import pathlib
from railway import app, Settings
from asyncio.subprocess import Process
import ssl
import socket as _socket


class Application(app.Application):
    ngrok: Union[str, pathlib.Path] = ...
    def __init__(self,
        ngrok: Union[str, pathlib.Path], 
        host: str=..., 
        port: int=..., 
        url_prefix: str=..., 
        *, 
        loop: asyncio.AbstractEventLoop=..., 
        settings: Settings=...,
        settings_file: Union[str, pathlib.Path]=..., 
        load_settings_from_env: bool=..., 
        ipv6: bool=..., 
        sock: _socket.socket=..., 
        worker_count: int=..., 
        use_ssl: bool=..., 
        ssl_context: ssl.SSLContext=...,                
        max_pending_connections: int=...,
        max_concurent_requests: int=...,
        connection_timeout: int=...,
        backlog: int=...,
        reuse_host: bool=...,
        reuse_port: bool=...
    ) -> None: ...
    @property
    def process(self) -> Optional[Process]: ...
    async def run_ngrok_executable(self) -> None: ...