import requests

r = requests.get('http://127.0.0.1:8080/', data='yes')
print(r.text)

r = requests.get('http://127.0.0.1:8080/', data='ok')
print(r.text)