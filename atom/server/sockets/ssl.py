from .utils import check_ellipsis
from .sockets import socket

import typing
import ssl as _ssl
import socket as _socket

__all__ = (
    'SSLSocket',
)

class SSLSocket(socket):

    def __init__(self):
        name = self.__class__.__name__
        raise TypeError(
            f"{name} does not have a public "
            f"constructor. Instances are returned by "
            f"{name}.wrap_socket()."
        )
        
    @classmethod
    def wrap_socket(cls, 
                sock: socket, 
                *, 
                server_side: bool=..., 
                server_hostname: str=..., 
                do_handshake_on_connect: bool=...,
                session: _ssl.SSLSession=...) -> 'SSLSocket':

        server_side = check_ellipsis(server_side, False)
        server_hostname = check_ellipsis(server_hostname, None)
        do_handshake_on_connect = check_ellipsis(do_handshake_on_connect, True)
        session = check_ellipsis(session, None)

        context: _ssl.SSLContext = sock._get('_socket__ssl')
        original: _socket.socket = sock._get('_socket__socket')

        if server_side:
            if server_hostname:
                raise ValueError("server_hostname can only be specified in client mode")

            if session:
                raise ValueError("session can only be specified in client mode")

        if context.check_hostname and not server_hostname:
            raise ValueError("check_hostname requires server_hostname")
        
        ssl = _ssl.SSLSocket._create(
            sock=original,
            server_hostname=server_hostname,
            server_side=server_side,
            do_handshake_on_connect=do_handshake_on_connect,
            context=context,
            session=session
        )   

        self = cls.__new__(cls)
        super(SSLSocket, self).__init__()
    
        self._server_hostname = server_hostname
        self._server_side = server_side
        self._handshake_on_connect = do_handshake_on_connect
        self._session = session

        self.__socket = ssl
        self.__original = sock

        return self

    @property
    def server_hostname(self) -> typing.Optional[str]:
        return self._server_hostname

    @property
    def server_side(self) -> bool:
        return self._server_side

    @property
    def do_handshake_on_connect(self) -> bool:
        return self._handshake_on_connect
        
    @property
    def session(self) -> typing.Optional[_ssl.SSLSession]:
        return self._session  

    def duplicate(self):
        raise NotImplementedError

    async def ssl_handshake(self):
        self._check_closed()
        self._check_connected()
        
        await self._run_in_executor('do_handshake', False)

    def compression(self) -> typing.Optional[str]:
        return self.__socket.compression()

    def cipher(self) -> typing.Optional[typing.Tuple[str, str, int]]:
        return self.__socket.cipher()

    def unwrap(self) -> socket:
        sock = self.__original
        return sock