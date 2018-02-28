import requests
import time
import random

t = int(time.time())
i = random.randint(0, 10000)
URL = (
    "http://localhost:8000/api/v1/kannel/receive/3dd1f9b8-a4c9-4411-9766-d4c3934ebc1d/?"
    "backend=yo&sender=256782820208&message=alert our nets were torn&ts=%s&id=%s" % (t, i))
print URL
res = requests.post(URL)
print res.text
