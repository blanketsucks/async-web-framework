# async-web-stuff

## Example Usages

### Basic Example

```py
import atom

app = atom.Application()

@app.route('/hello/{name}', 'GET')
async def get_name(ctx: atom.Context, name: str):
    if len(name) > 64:
        error = {
            'error': 'name too long.
        }
        return atom.abort(400, message=error, content_type='application/json')

    ctx.build_json_response({'Hello there': name})
    return ctx

if __name__ == '__main__':
    app.run()

```

### Views Examle

```py
import atom

app = atom.Application()
app.users = {}

@app.view('/users') # Either this or class UsersView(atom.HTTPView, path='/users'), both work
class UsersView(atom.HTTPView):
    async def get(self, request: atom.Request):
        return app.users

if __name__ == '__main__':
    app.run()
```
