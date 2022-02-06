from subway import Application, Request, models

class User(models.Model):
    name: str

app = Application()

@app.route('/users', 'POST')
async def create_user(request: Request[Application], user: User):
    return user

app.run()