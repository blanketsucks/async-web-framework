from wsgi import restful

app = restful.App()

class Endpoint(restful.Extension, name='endpoint_test'):
    pass

class Extension(restful.Endpoint, name='extension_test'):
    pass

app.add_endpoint(Extension, '/test')
app.add_extension(Endpoint(app))

print(app.extensions)
print(app.endpoints)

if __name__ == '__main__':
    app.run() 

