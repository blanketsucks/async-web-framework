import functools
import atom
import asyncio

app = atom.Application()
handler = atom.RatelimiteHandler()

def handle_ratelimits(rate: int, per: int):
    def decorator(route: atom.Route) -> atom.Route:
        bucket = handler.add_bucket(route.path, rate=rate, per=per)

        @functools.wraps(route.callback)
        async def wrapper(request: atom.Request):
            if request.method not in bucket.keys:
                bucket.add_key(request.method)

            try:
                bucket.update_ratelimit(request, request.method)
            except atom.Ratelimited as e:
                return atom.Response(
                    status=429,
                    headers={'Retry-After': str(e.retry_after)},
                    body='Ratelimit exceeded'
                )

            return await route.callback(request)
        return wrapper
    return decorator

@handle_ratelimits(rate=2, per=0.3)
@app.route('/')
async def main(request: atom.Request):
    return 'yes'

@main.middleware
async def middleware(route: atom.Route, request: atom.Request):
    if request.text() == 'ok':
        await request.send('no')
        await request.close()

        return

asyncio.run(atom.run(app))