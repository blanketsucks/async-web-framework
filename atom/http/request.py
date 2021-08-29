from typing import Any, Dict, Optional

class Request:
    def __init__(self, 
                method: str, 
                path: str, 
                host: str, 
                headers: Dict[str, Any],
                body: Optional[str]) -> None:
        self.method = method
        self.path = path
        self.host = host
        self.headers = headers
        self.body = body

        self.headers['Host'] = host

    def __repr__(self) -> str:
        return '<Request method={0.method!r} host={0.host!r} path={0.path!r}>'.format(self)

    def encode(self):
        request = [f'{self.method} {self.path} HTTP/1.1']

        request.extend(f'{k}: {v}' for k, v in self.headers.items())
        request.append('\r\n')

        if self.body:
            request.append(self.body)

        request = b'\r\n'.join(part.encode() for part in request)
        return request
