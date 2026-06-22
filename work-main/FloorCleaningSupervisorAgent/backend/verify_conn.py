import os
import requests
from app.core.database import users_container

os.chdir(r"C:\Users\ravir\work\FloorCleaningSupervisorAgent\backend")

print('db_adapter=', type(users_container).__name__)
try:
    count = len(list(users_container.read_all_items()))
    print('db_read_count=', count)
except Exception as e:
    print('db_read_error=', repr(e))

urls = [
    'http://127.0.0.1:8010/cors-test',
    'http://127.0.0.1:8010/docs'
]

for url in urls:
    try:
        r = requests.get(url, timeout=10)
        print(f'URL={url} STATUS={r.status_code} CONTENT_TYPE={r.headers.get("content-type")}')
        print(r.text[:400])
    except Exception as e:
        print(f'URL={url} ERROR={repr(e)}')
