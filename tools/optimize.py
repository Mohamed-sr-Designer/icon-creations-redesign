"""Create web-optimized WebP derivatives (max 1600px) of every downloaded image. Originals are kept untouched."""
import os, json, concurrent.futures as cf
from PIL import Image, ImageSequence
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, 'docs')
OUT = os.path.join(DOCS, '_opt')
dims = {}
def job(src):
    rel = os.path.relpath(src, DOCS)
    dst = os.path.join(OUT, rel) + '.webp'
    try:
        im = Image.open(src)
        w, h = im.size
        dims[rel.replace(os.sep, '/')] = [w, h]
        if getattr(im, 'is_animated', False): return  # keep animated GIFs as-is
        if os.path.exists(dst): return
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        im = im.convert('RGBA') if im.mode in ('P', 'LA', 'RGBA') else im.convert('RGB')
        if w > 1600: im = im.resize((1600, round(h * 1600 / w)), Image.LANCZOS)
        im.save(dst, 'WEBP', quality=80, method=4)
    except Exception as e:
        print('skip', rel, e)
files = []
for d, _, fs in os.walk(DOCS):
    if d.startswith(OUT): continue
    for f in fs:
        if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')): files.append(os.path.join(d, f))
with cf.ThreadPoolExecutor(8) as ex: list(ex.map(job, files))
json.dump(dims, open(os.path.join(ROOT, '_audit', 'dims.json'), 'w'), indent=0)
print('images', len(files), 'dims', len(dims))
