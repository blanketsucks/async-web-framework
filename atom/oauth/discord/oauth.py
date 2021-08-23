from typing import Dict, List, Optional
from urllib.parse import urlencode
from atom import http

from atom import Request
from .session import Session
from atom.oauth.abc import AbstarctOauth2Client

class Oauth2Client(AbstarctOauth2Client):
    URL = 'https://discordapp.com/api/oauth2/authorize'
    def __init__(self, 
                client_id: str, 
                client_secret: str, 
                redirect_uri: str,
                *,
                session: http.HTTPSession=None) -> None:
        self.client_id = client_id
        self.redirect_uri = redirect_uri
        self.client_secret = client_secret
        self.session = session or http.HTTPSession()

        self._sessions = {}

    @property
    def sessions(self) -> Dict[str, Session]:
        return self._sessions

    def redirect(self, request: Request, *, state: str=None, scopes: List[str]=None):
        scopes = scopes or ['identify']
        scopes = ' '.join(scopes)

        params = {
            'client_id': self.client_id,
            'scope': scopes,
            'redirect_uri': self.redirect_uri,
            'response_type': 'code', 
        }

        if state:
            params['state'] = state

        params = urlencode(params)
        return request.redirect(f'{self.URL}?{params}')

    def get_session(self, access_token: str) -> Optional[Session]:
        return self._sessions.get(access_token)

    async def create_session(self, code: str):
        session = Session(
            code=code,
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=self.redirect_uri,
            session=self.session,
        )
        await session.fetch_token()

        self._sessions[session.access_token] = session
        return session

    async def close(self):
        for session in self._sessions.values():
            await session.close()

        await self.session.close()
        self._sessions.clear()

        return self