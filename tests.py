import atom
from atom import restful
import falcon

shard = atom.Shard('my_shard')
app = restful.RESTApplication()

app.register_shard(shard)

print(app.shards)