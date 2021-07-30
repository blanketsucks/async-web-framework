import aiohttp
from typing import Dict, List, Optional
from urllib.parse import urlencode

from atom import Request
from .session import Session
from ..abc import AbstarctOauth2Client

class Oauth2Client(AbstarctOauth2Client):
    URL = 'https://github.com/login/oauth/authorize'
    def __init__(self, 
                client_id: str, 
                client_secret: str, 
                redirect_uri: str, 
                *, 
                session: aiohttp.ClientSession=None) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.session = session or aiohttp.ClientSession()

        self._sessions = {}

    @property
    def sessions(self) -> Dict[str, 'Session']:
        return self._sessions

    def redirect(self, request: Request, *, state: str=None, scopes: List[str]=None):
        scopes = scopes or ['user', 'repo']
        scopes = ', '.join(scopes)

        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'scope': scopes
        }

        if state:
            params['state'] = state

        params = urlencode(params)
        return request.redirect(f'{self.URL}?{params}')

    def get_session(self, code: str) -> Optional[Session]:
        return self._sessions.get(code)
        
    def create_session(self, code: str) -> 'Session':
        session = Session(
            client_id=self.client_id,
            client_secret=self.client_secret,
            code=code,
            redirect_uri=self.redirect_uri,
            session=self.session
        )

        self._sessions[code] = session
        return session