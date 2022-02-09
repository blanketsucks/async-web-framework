from subway import Application, Request

# If templates_dir is not specified, the default is 'templates'
app = Application()

@app.route('/home')
async def home(request: Request[Application]):
    # This works the same way as flask's render_template
    return await request.app.render('home.html', title='Home')

app.run()