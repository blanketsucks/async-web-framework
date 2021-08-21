import requests

json = {'user': {'name': 'John Doe'}}
r = requests.post('http://127.0.0.1:8080/', json=json)