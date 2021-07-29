from typing import TYPE_CHECKING
import aiohttp

from .guild import Guild

if TYPE_CHECKING:
    from .session import Session

class Avatar:
    def __init__(self, user: 'User') -> None:
        self.user = user

    async def read(self, extension: str=None) -> bytes:
        if not extension:
            extension = 'jpg'

        hash = self.user._payload['avatar']
        id = self.user.id
        session = self.user._session.session

        async with session.get(f'https://cdn.discordapp.com/avatars/{id}/{hash}.{extension}') as response:
            return await response.read()

class User:
    def __init__(self, data, session: 'Session') -> None:
        self._payload = data
        self._session = session

        self.id: int = data['id']
        self.username: str = data['username']
        self.discriminator: int = data['discriminator']

    @property
    def avatar(self):
        return Avatar(self)

    async def fetch_guilds(self):
        guilds = await self._session.request('/users/@me/guilds')
        return guilds