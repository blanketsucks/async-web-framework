from urllib.parse import urlencode

class self:
    client_id = 'client_id'
    client_secret = 'client_secret'
    redirect_uri = 'http://localhost:8000/'

state = '1'
prompt = '123'

scopes = ['identify']
scopes = ', '.join(scopes)

params = {
    'client_id': self.client_id,
    'redirect_uri': self.redirect_uri,
    'scope': scopes,
    'response_type': 'code', 
}

if state:
    params['state'] = state

if prompt:
    params['prompt'] = prompt

params = urlencode(params)
print(params)