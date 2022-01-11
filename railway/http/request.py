from typing import Any, Dict

class HTTPRequest:
    """
    An HTTP request.
    
    Parameters
    ----------
    method: :class:`str`
        The HTTP method.
    path: :class:`str`
        The path of the request.
    host: :class:`str`
        The host of the request.
    headers: :class:`dict`
        The headers of the request.
    body: Any
        The body of the request.
    """
    def __init__(
        self,
        method: str,
        path: str,
        host: str,
        headers: Dict[str, Any],
        body: Any
    ) -> None:
        self.method = method
        self.path = path
        self.host = host
        self.headers = headers
        self.body = body

        self.headers['Host'] = host

    def __repr__(self) -> str:
        return '<Request method={0.method!r} host={0.host!r} path={0.path!r}>'.format(self)

    def prepare(self) -> bytes:
        """
        Encodes the request into a bytes object.
        """
        request = [f'{self.method} {self.path} HTTP/1.1']

        request.extend(f'{k}: {v}' for k, v in self.headers.items())
        request.append('\r\n')

        if self.body is not None:
            request.append(self.body)

        return b'\r\n'.join(part.encode() for part in request)
