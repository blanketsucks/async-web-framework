from typing import List

class Icon:
    def __init__(self, guild: 'Guild') -> None:
        self.guild = guild

    async def read(self) -> bytes:
        url = f'https://cdn.discordapp.com/icons/{self.guild.id}/{self.guild._payload["icon"]}.jpg'
        session = self.guild._session.session

        async with session.get(url) as resp:
            return await resp.read()
        

class Guild:
    def __init__(self, data, session) -> None:
        self._payload = data
        self._session = session

        self.id: int = self._payload['id']
        self.name: str = self._payload['name']
        self.features: List[str] = self._payload['features']

    @property
    def icon(self):
        return Icon(self)

    def to_dict(self):
        return self._payload