from typing import Dict, List, Optional
from urllib.parse import urlencode

from atom import Request
from .session import Session
from atom.http import HTTPSession
from atom.oauth.abc import AbstarctOauth2Client

class Oauth2Client(AbstarctOauth2Client):
    URL = 'https://github.com/login/oauth/authorize'
    def __init__(self, 
                client_id: str, 
                client_secret: str, 
                redirect_uri: str, 
                *, 
                session: HTTPSession=None) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.session = session or HTTPSession()

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

    def get_session(self, access_token: str) -> Optional[Session]:
        return self._sessions.get(access_token)
        
    async def create_session(self, code: str) -> 'Session':
        session = Session(
            client_id=self.client_id,
            client_secret=self.client_secret,
            code=code,
            redirect_uri=self.redirect_uri,
            session=self.session
        )
        await session.fetch_token()

        self._sessions[session.access_token] = session
        return session