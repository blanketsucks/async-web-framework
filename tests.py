import atom

app = atom.Application()
app.last_request = None
app.second_last_request = None

@app.route('/yes', 'GET')
async def yes(ctx: atom.Context):
    print(ctx.status)
    app.last_request = ctx.request.datetime
    return ctx.build_response('yes')

@app.route('/no', 'GET')
async def no(ctx: atom.Context):
    app.second_last_request = ctx.request.datetime
    return ctx.build_response('no')

@app.get('/maybe')
async def maybe(ctx: atom.Context):
    m = app.last_request - app.second_last_request
    print(m)

    return await ctx.redirect('/yes')

app.run()