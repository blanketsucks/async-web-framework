import requests

for i in range(10000):
    r = requests.get('http://127.0.0.1:8080/')
    print(r.text)