from typing import Optional

from atom.http import HTTPSession
from atom.oauth.abc import AbstractSession

class Session(AbstractSession):
    URL = 'https://github.com/login/oauth/access_token'
    def __init__(self, 
                code: str, 
                client_id: str, 
                client_secret: str, 
                redirect_uri: str, 
                session: HTTPSession) -> None:

        self.code = code
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.session = session
        self._access_token = None

    @property
    def access_token(self) -> Optional[str]:
        return self._access_token

    async def fetch_token(self):
        pass