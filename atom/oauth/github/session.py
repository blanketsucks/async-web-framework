import aiohttp

from ..abc import AbstractSession

class Session(AbstractSession):
    URL = 'https://github.com/login/oauth/access_token'
    def __init__(self, 
                code: str, 
                client_id: str, 
                client_secret: str, 
                redirect_uri: str, 
                session: aiohttp.ClientSession) -> None:
        self.code = code
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.session = session

    async def fetch_token(self):
        pass