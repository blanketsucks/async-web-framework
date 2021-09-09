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
from typing import Any, Dict, Optional

class HTTPRequest:
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
