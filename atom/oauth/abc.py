import aiohttp
from typing import List, Optional

from atom import Request

class AbstarctOauth2Client:
    def __init__(self,                
                client_id: str, 
                client_secret: str, 
                redirect_uri: str,
                *,
                session: aiohttp.ClientSession=None) -> None:
        ...

    def redirect(self, request: Request, *, state: str=None, scopes: List[str]=None):
        raise NotImplementedError

    def get_session(self, access_token: str) -> Optional['AbstractSession']:
        raise NotImplementedError

    def create_session(self, access_token: str) -> 'AbstractSession':
        raise NotImplementedError

    async def close(self):
        raise NotImplementedError

class AbstractSession:
    URL: str
    def __init__(self,
                code: str, 
                client_id: str, 
                client_secret: str,
                redirect_uri: str, 
                session: aiohttp.ClientSession) -> None:
        ...

    async def fetch_token(self):
        raise NotImplementedError

    async def request(self, url: str, method: str=None):
        raise NotImplementedError

    async def close(self) -> None:
        raise NotImplementedError