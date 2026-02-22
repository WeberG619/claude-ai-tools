"""List all CDP targets"""
import urllib.request, json
targets = json.loads(urllib.request.urlopen('http://127.0.0.1:9222/json', timeout=5).read().decode())
for i, t in enumerate(targets):
    print(f"{i}: [{t['type']}] {t['title'][:70]} | {t['url'][:90]}")
