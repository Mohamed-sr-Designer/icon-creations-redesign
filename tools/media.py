"""Collect every media URL referenced by the extracted content and mirror it into docs/ at its original path."""
import json, os, re, urllib.parse, urllib.request, concurrent.futures as cf
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = json.load(open(os.path.join(ROOT, '_audit', 'content.json'), encoding='utf-8'))
EXTRA = ['https://icon-creations.com/uploads/news/main/18_398x244.jpg', 'https://icon-creations.com/uploads/blog/main/12_cover_399x244.png', 'https://icon-creations.com/images/news-latest.jpg', 'https://icon-creations.com/images/icon-creations-logo-white.png', 'https://icon-creations.com/images/icon-creations-logo.png',
         'https://icon-creations.com/favicon/favicon.ico', 'https://icon-creations.com/favicon/apple-touch-icon.png',
         'https://icon-creations.com/favicon/favicon-32x32.png', 'https://icon-creations.com/favicon/favicon-16x16.png']
urls = set(EXTRA)
def walk(o):
    if isinstance(o, dict):
        for k, v in o.items():
            if k in ('src', 'tablet', 'mobile', 'img', 'icon', 'bg', 'poster') and isinstance(v, str) and v.startswith('https://icon-creations.com/'):
                urls.add(v)
            else: walk(v)
    elif isinstance(o, list):
        for x in o: walk(x)
walk([p for p in P if p['type'] != 'junk'])
def local(u):
    path = urllib.parse.unquote(urllib.parse.urlparse(u).path)
    return os.path.join(ROOT, 'docs', *path.strip('/').split('/'))
res = {}
def get(u):
    dst = local(u)
    if os.path.exists(dst) and os.path.getsize(dst) > 0: res[u] = ('ok', os.path.getsize(dst)); return
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    q = urllib.parse.urlsplit(u); q = urllib.parse.urlunsplit((q.scheme, q.netloc, urllib.parse.quote(urllib.parse.unquote(q.path)), q.query, ''))
    for _ in range(3):
        try:
            b = urllib.request.urlopen(urllib.request.Request(q, headers={'User-Agent': 'Mozilla/5.0'}), timeout=60).read()
            open(dst, 'wb').write(b); res[u] = ('ok', len(b)); return
        except Exception as e: err = str(e)
    res[u] = ('missing', err)
with cf.ThreadPoolExecutor(12) as ex: list(ex.map(get, sorted(urls)))
json.dump(res, open(os.path.join(ROOT, '_audit', 'media.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
ok = [v for v in res.values() if v[0] == 'ok']
print('media', len(res), 'ok', len(ok), 'MB', round(sum(v[1] for v in ok) / 1e6, 1))
for u, v in res.items():
    if v[0] != 'ok': print('MISSING', u, v[1][:60])
