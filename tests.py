import atom

app = atom.Application()
shard = atom.Shard()

@app.get('/api/users/{username}/guild/{guildid}')
async def get_guild_user(request: atom.Request, username: str, guildid: int):
    return f'{username}, {guildid}'


if __name__ == '__main__':
    app.run()