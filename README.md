# async-web-stuff

## Example Usages

### Basic Example

```py
import atom

app = atom.Application()

@app.route('/hello/{name}', 'GET')
async def get_name(request: atom.Request, name: str):
    if len(name) > 25:
        error = {
            'message': 'name too long.',
            'status': 400
        }
        return error, 400

    return {
        'Hello': name
    }

if __name__ == '__main__':
    app.run()
```

### Websocket Example
```py
import atom

app = atom.Application()

@app.websocket('/ws')
async def ws(request: atom.Request, ws: atom.Websocket):
    while True:
        message = await ws.receive_str()
        print(message)

        await ws.send_str(message)

if __name__ == '__main__':
    app.run()
```

### Views Example

```py
import atom

app = atom.Application()
app.users = {}

@app.view('/users') # Either this or class UsersView(atom.HTTPView, path='/users'), both work
class UsersView(atom.HTTPView):
    async def get(self, request: atom.Request):
        return request.app.users

if __name__ == '__main__':
    app.run()
```

### Resource Example with ratelimits
```py
from typing import Dict
import atom

app = atom.Application()

class User(atom.Model):
    name: str
    id: int

@app.resource()
class Users(atom.Resource):
    def __init__(self) -> None:
        self.users: Dict[int, User] = {}
        self.ratelimiter = atom.RatelimiteHandler()

        self.ratelimiter.add_bucket(
            path='/users',
            rate=5,
            per=1
        )

    def update_ratelimiter(self, path: str, request: atom.Request):
        bucket = self.ratelimiter.get_bucket(path)

        try:
            bucket.update_ratelimit(request, request.client_ip)
        except atom.Ratelimited as e:
            message = {
                'message': 'Ratelimit exceeded. Please try again later.'
            }

            response = atom.JSONResponse(body=message, status=427)
            response.add_header('Retry-After', e.retry_after)

            return response

        return None

    @atom.route('/users', 'GET')
    async def get_all_users(self, request: atom.Request):
        resp = self.update_ratelimiter('/users', request)
        if resp:
            return resp

        users = [user.json() for user in self.users.values()]
        return users

    @atom.route('/users', 'POST')
    async def create_user(self, request: atom.Request, user: User):
        resp = self.update_ratelimiter('/users', request)
        if resp:
            return resp

        if user.id in self.users:
            return {
                'message': 'user already exists.',
            }, 400

        self.users[user.id] = user
        return user, 201

    @atom.route('/users/{id}', 'DELETE')
    async def delete_user(self, request: atom.Request, id: int):
        user = self.users.pop(id, None)
        if not user:
            return {
                'message': 'user not found.',
            }, 404

        return user, 204

    @atom.route('/users/{id}', 'GET')
    async def get_user(self, request: atom.Request, id: int):
        user = self.users.get(id)
        if not user:
            return {
                'message': 'user not found.',
            }, 404

        return user

if __name__ == '__main__':
    app.run()
```

