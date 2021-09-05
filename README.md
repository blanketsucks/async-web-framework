# async-web-stuff

## Example Usages

### Basic Example

```py
import railway

app = railway.Application()

@app.route('/hello/{name}', 'GET')
async def get_name(request: railway.Request, name: str):
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
import railway

app = railway.Application()

@app.websocket('/ws')
async def ws(request: railway.Request, ws: railway.Websocket):
    while True:
        await ws.send(b'Hello!')

        data = await ws.receive()
        print(data.data)


if __name__ == '__main__':
    app.run()
```

### Views Example

```py
import railway

app = railway.Application()
app.users = {}

@app.view('/users') # Either this or class UsersView(railway.HTTPView, path='/users'), both work
class UsersView(railway.HTTPView):
    async def get(self, request: railway.Request):
        return request.app.users

if __name__ == '__main__':
    app.run()
```

### Resource Example with ratelimits
```py
from typing import Dict
import railway

app = railway.Application()

class User(railway.Model):
    name: str
    id: int

@app.resource()
class Users(railway.Resource):
    def __init__(self) -> None:
        self.users: Dict[int, User] = {}
        self.ratelimiter = railway.RatelimiteHandler()

        self.ratelimiter.add_bucket(
            path='/users',
            rate=5,
            per=1
        )

    def update_ratelimiter(self, path: str, request: railway.Request):
        bucket = self.ratelimiter.get_bucket(path)

        try:
            bucket.update_ratelimit(request, request.client_ip)
        except railway.Ratelimited as e:
            message = {
                'message': 'Ratelimit exceeded. Please try again later.'
            }

            response = railway.JSONResponse(body=message, status=427)
            response.add_header('Retry-After', e.retry_after)

            return response

        return None

    @railway.route('/users', 'GET')
    async def get_all_users(self, request: railway.Request):
        resp = self.update_ratelimiter('/users', request)
        if resp:
            return resp

        users = [user.json() for user in self.users.values()]
        return users

    @railway.route('/users', 'POST')
    async def create_user(self, request: railway.Request, user: User):
        resp = self.update_ratelimiter('/users', request)
        if resp:
            return resp

        if user.id in self.users:
            return {
                'message': 'user already exists.',
            }, 400

        self.users[user.id] = user
        return user, 201

    @railway.route('/users/{id}', 'DELETE')
    async def delete_user(self, request: railway.Request, id: int):
        user = self.users.pop(id, None)
        if not user:
            return {
                'message': 'user not found.',
            }, 404

        return user, 204

    @railway.route('/users/{id}', 'GET')
    async def get_user(self, request: railway.Request, id: int):
        user = self.users.get(id)
        if not user:
            return {
                'message': 'user not found.',
            }, 404

        return user

if __name__ == '__main__':
    app.run()
```

