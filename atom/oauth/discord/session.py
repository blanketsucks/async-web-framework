from typing import Optional
import aiohttp

from .user import User
from ..abc import AbstractSession
from ..errors import SessionClosed 

class Session(AbstractSession):
    URL = 'https://discord.com/api/v8/'
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

        self._access_token = None
        self._user: Optional[User] = None
        self._closed = False

    @property
    def access_token(self):
        return self._access_token

    @property
    def user(self):
        return self._user

    def is_closed(self):
        return self._closed

    async def fetch_token(self):
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': self.code,
            'grant_type': 'authorization_code',
            'redirect_uri': self.redirect_uri
        }
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        async with self.session.post('https://discord.com/api/v8/oauth2/token', data=data, headers=headers) as resp:
            data = await resp.json()

            self._access_token = data['access_token']
            return data

    async def request(self, url: str, method: str=None):
        if self._closed:
            raise SessionClosed

        if not self._access_token:
            await self.fetch_token()

        if not method:
            method = 'GET'

        headers = {
            'Authorization': 'Bearer ' + self._access_token
        }

        async with self.session.request(method, self.URL + url, headers=headers) as resp:
            return await resp.json()

    async def fetch_user(self):
        data = await self.request('users/@me')
        user = User(data, self)

        self._user = user
        return user

    async def close(self):
        data = {
            'token': self._access_token
        }

        url = 'https://discord.com/api/v8/oauth2/token/revoke'
        headers = {
            'Authorization': 'Bearer ' + self._access_token,
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        async with self.session.post(url, headers=headers, data=data):
            self._closed = True
        

        