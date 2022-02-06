from subway import Application, Request, HTTPView

app = Application()

@app.view() # Pass in `path` here or in the class kwargs.
class View(HTTPView, path='/hello/{name}'): # Parameters also work with views.
    async def get(self, request: Request, name: str):
        return name

app.add_view(View) 
# Adds the view to the application.
# the following is also works: app.add_view(View())
# or, if you want to use a decorator, decorate the view with the decorator: