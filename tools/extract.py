"""Extract every page of the original icon-creations.com into a structured content model.

Input : _audit/raw/_index.json + _audit/bytes/*.html (byte-exact crawl of the live site)
Output: _audit/content.json (one entry per page; text kept verbatim, media kept by original URL)
"""
import json, re, os, sys, hashlib, urllib.parse
from bs4 import BeautifulSoup, NavigableString, Comment, Tag

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUD = os.path.join(ROOT, '_audit')
BASE = 'https://icon-creations.com'
IDX = json.load(open(os.path.join(AUD, 'raw', '_index.json'), encoding='utf-8'))


def smart_decode(b):
    """UTF-8 with per-byte cp1252 fallback (the live site mixes encodings)."""
    return b.decode('utf-8', 'cp1252fallback')


import codecs


def _cp1252_fallback(err):
    bad = err.object[err.start:err.end]
    return bad.decode('cp1252', 'replace'), err.end


codecs.register_error('cp1252fallback', _cp1252_fallback)


def load(u):
    return smart_decode(open(os.path.join(AUD, 'bytes', IDX[u]['file']), 'rb').read())


def norm(t):
    return re.sub(r'\s+', ' ', t or '').strip()


def absu(src, page):
    if not src: return ''
    src = src.strip()
    if src.startswith(('mailto:', 'tel:', 'javascript:', '#')): return src
    return urllib.parse.urljoin(page if page.endswith('/') else page + '/', src) if not src.startswith('http') else src


def absu_img(src, page):
    # relative image paths on the old site resolve against the page directory as the browser saw it
    if not src: return ''
    src = src.strip()
    if src.startswith('http'): return src
    if src.startswith('/'): return BASE + src
    # page urls are served without trailing slash; browser resolves relative to parent dir
    return urllib.parse.urljoin(page, src)


INLINE_OK = {'a', 'br', 'strong', 'b', 'em', 'i', 'u', 'sup', 'sub'}


def inline_html(el, page):
    """Sanitize inline content but keep every character of text."""
    parts = []
    for c in el.children:
        if isinstance(c, Comment): continue
        if isinstance(c, NavigableString):
            t = str(c)
            parts.append(t.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))
            continue
        if not isinstance(c, Tag): continue
        if c.name in ('script', 'style', 'img', 'iframe'): continue
        inner = inline_html(c, page)
        if c.name == 'a':
            href = c.get('href') or ''
            if href and not href.startswith('javascript'):
                href = absu(href, page)
                parts.append(f'<a href="{href}">{inner}</a>')
            else:
                parts.append(inner)
        elif c.name == 'br':
            parts.append('<br>')
        elif c.name == 'small':
            parts.append(f'<small>{inner}</small>')
        elif c.name in ('strong', 'b'):
            parts.append(f'<strong>{inner}</strong>')
        elif c.name in ('em', 'i'):
            if 'fa' in ' '.join(c.get('class', [])): continue  # font-awesome icon
            parts.append(f'<em>{inner}</em>')
        elif c.name in ('ul', 'ol'):
            lis = ''.join(f'<li>{inline_html(li, page)}</li>' for li in c.find_all('li', recursive=False))
            parts.append(f'<{c.name}>{lis}</{c.name}>')
        elif c.name in ('p', 'div') :
            parts.append(inner + '<br>')
        else:
            parts.append(inner)
    h = ''.join(parts)
    h = re.sub(r'\s+', ' ', h)
    h = re.sub(r'(\s*<br>\s*)+$', '', h).strip()
    return h


def text_of(el):
    return norm(el.get_text(' '))


SKIP_CLASSES = {'overlay', 'swiper-pagination', 'wrkdtls-arr', 'swiper-button-next', 'swiper-button-prev',
                'hero-paging', 'loading', 'brdcrumb'}
RESP_ALT = ('tablet', 'mobile')


def classes(el):
    return el.get('class', []) if isinstance(el, Tag) else []


def is_hidden_variant(el):
    c = classes(el)
    if any(x in c for x in RESP_ALT): return True
    return False


class Walker:
    def __init__(self, page):
        self.page = page
        self.seen_img = set()
        self.last_text = None

    def img_block(self, el):
        src = el.get('src') or el.get('data-src') or ''
        if not src: return None
        src = absu_img(src, self.page)
        return {'t': 'img', 'src': src, 'alt': norm(el.get('alt', ''))}

    def responsive_img(self, el):
        """desktop img + sibling tablet/mobile variants -> one picture block"""
        b = self.img_block(el)
        if not b: return None
        par = el.parent
        for sib in par.find_all('img', recursive=False):
            c = classes(sib)
            for k in RESP_ALT:
                if k in c:
                    b[k] = absu_img(sib.get('src'), self.page)
        return b

    def walk(self, el, out):
        for c in el.children:
            if isinstance(c, Comment): continue
            if isinstance(c, NavigableString):
                t = norm(str(c))
                if t:
                    self.emit_p(out, t.replace('&', '&amp;').replace('<', '&lt;'), t)
                continue
            if not isinstance(c, Tag): continue
            self.node(c, out)

    def emit_p(self, out, html, txt):
        if not txt: return
        if txt == self.last_text: return  # responsive duplicate (desktop/tablet/mobile copies)
        self.last_text = txt
        out.append({'t': 'p', 'html': html})

    def node(self, c, out):
        cl = classes(c)
        name = c.name
        if name in ('script', 'style', 'noscript', 'link', 'meta', 'nav', 'footer', 'button'):
            if name == 'button':
                t = text_of(c)
                if t: out.append({'t': 'label', 'text': t})
            return
        if any(x in SKIP_CLASSES for x in cl): return
        if c.get('id') and name in ('div', 'section', 'span', 'a') and not c.get('id', '').startswith(('popup', 'work-tabs')):
            out.append({'t': 'anchor', 'id': c.get('id')})
        if 'work-popup' in cl: return  # gallery popup duplicates (same images already in the grid)
        if 'display:none' in (c.get('style') or '').replace(' ', ''):
            t = text_of(c)
            if t: out.append({'t': 'p', 'html': inline_html(c, self.page), 'hidden': True})
            return
        if name == 'a' and any(x.startswith('popup-btn') for x in cl):
            out.append({'t': 'share', 'net': ' '.join(x for x in cl if x != 'popup-btn'), 'href': c.get('href', '')})
            return
        if name in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            sm = c.find('small')
            eyebrow = ''
            first = next((x for x in c.children if not (isinstance(x, NavigableString) and not x.strip())), None)
            if first is not None and getattr(first, 'name', None) == 'span':
                first = next((x for x in first.children if not (isinstance(x, NavigableString) and not x.strip())), None)
            if sm and first is sm:
                eyebrow = text_of(sm)
                sm.extract()
            html = inline_html(c, self.page)
            txt = text_of(c)
            if not txt and not eyebrow: return
            out.append({'t': 'h', 'lvl': int(name[1]), 'eyebrow': eyebrow, 'html': html,
                        'ar': 'ar' in cl})
            self.last_text = None
            return
        if name == 'img':
            if is_hidden_variant(c): return
            b = self.responsive_img(c) if 'desktop' in cl else self.img_block(c)
            if b:
                out.append(b)
            return
        if name == 'iframe':
            src = (c.get('src') or c.get('data-src') or '').strip()
            if 'google.com/maps' in src:
                out.append({'t': 'map', 'src': src, 'text': text_of(c)})
            elif src:
                out.append({'t': 'video', 'src': src, 'kind': 'iframe'})
            return
        if name == 'video':
            srcs = [absu_img(s.get('src'), self.page) for s in c.find_all('source') if s.get('src')]
            if c.get('src'): srcs.insert(0, absu_img(c.get('src'), self.page))
            if srcs:
                out.append({'t': 'video', 'src': srcs[0], 'kind': 'file', 'fallback': text_of(c),
                            'poster': absu_img(c.get('poster'), self.page) if c.get('poster') else ''})
            return
        if name == 'form':
            out.append(self.form(c))
            return
        if 'numscroller' in cl:
            return
        if c.find(class_='numscroller', recursive=False) or (c.select_one('.numscroller') and len(c.select('.numscroller')) == 1 and name == 'div' and len(text_of(c)) < 60 and not c.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])):
            num = c.select_one('.numscroller')
            suffix = num.find_next_sibling('span')
            lab = c.find('p')
            out.append({'t': 'stat', 'num': text_of(num), 'suffix': text_of(suffix) if suffix else '',
                        'label': inline_html(lab, self.page) if lab else ''})
            return
        if name in ('ul', 'ol'):
            lis = c.find_all('li', recursive=False)
            if lis and all(not li.find(['img', 'h1', 'h2', 'h3', 'h4', 'div', 'iframe']) for li in lis):
                items = [inline_html(li, self.page) for li in lis]
                items = [i for i in items if norm(re.sub('<[^>]+>', '', i))]
                if items:
                    out.append({'t': 'list', 'ordered': name == 'ol', 'items': items,
                                'tabs': 'h-work-tabs' in ' '.join(classes(c.parent)) or 'work-filter' in cl})
                return
            self.walk(c, out)
            return
        if name == 'a':
            href = c.get('href') or ''
            for fr in c.find_all(['iframe', 'video']):
                self.node(fr, out)
                fr.extract()
            imgs = c.find_all('img')
            t = text_of(c)
            if not imgs and not t: return
            if imgs and t and href and not href.startswith('#'):
                strong = c.find('strong')
                small = c.find('small')
                span = c.find('span')
                main = [i for i in imgs if 'serv-icon' not in classes(i)]
                icon = [i for i in imgs if 'serv-icon' in classes(i)]
                card = {'t': 'card', 'href': absu(href, self.page),
                        'img': absu_img((main or imgs)[0].get('src'), self.page),
                        'alt': norm((main or imgs)[0].get('alt', '')),
                        'icon': absu_img(icon[0].get('src'), self.page) if icon else '',
                        'icon_alt': norm(icon[0].get('alt', '')) if icon else '',
                        'title': text_of(strong) if strong else (inline_html(span, self.page) if span else t),
                        'meta': text_of(small) if small else ''}
                out.append(card)
                return
            if imgs and href.startswith('#popup'):
                for i in imgs:
                    b = self.img_block(i)
                    if b: out.append(b)
                return
            if imgs and not t:
                for i in imgs:
                    b = self.img_block(i)
                    if b:
                        b['href'] = absu(href, self.page) if href and not href.startswith(('#', 'javascript')) else ''
                        out.append(b)
                return
            if t:
                if href.startswith('javascript') or href == '#':
                    out.append({'t': 'label', 'text': t})
                else:
                    out.append({'t': 'btn', 'text': t, 'href': absu(href, self.page),
                                'popup': href if href.startswith('#popup') else ''})
                self.last_text = None
            return
        if 'swiper-container' in cl and 'hero-slider' not in cl:
            slides = []
            for s in c.select('.swiper-slide'):
                sub = []
                w = Walker(self.page)
                w.walk(s, sub)
                if sub: slides.append(sub)
            if slides:
                out.append({'t': 'slider', 'slides': slides})
            return
        if name in ('p', 'font', 'span', 'strong', 'b', 'em', 'label', 'small') or (
                name == 'div' and c.find(['div', 'p', 'img', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'iframe', 'a', 'form', 'video', 'section', 'table']) is None):
            # leaf text container
            if name == 'p' and is_hidden_variant(c) and text_of(c) == self.last_text: return
            imgs = c.find_all('img')
            for i in imgs:
                if is_hidden_variant(i): continue
                b = self.img_block(i)
                if b: out.append(b)
            for f in c.find_all('iframe'):
                self.node(f, out)
            if name == 'p' and c.find('a') and len(c.find_all('a')) == 1 and text_of(c) == text_of(c.find('a')) and 'btn' in ' '.join(classes(c.find('a'))):
                self.node(c.find('a'), out); return
            txt = text_of(c)
            if txt:
                self.emit_p(out, inline_html(c, self.page), txt)
            return
        if name == 'table':
            out.append({'t': 'table', 'html': str(c)})
            return
        self.walk(c, out)

    def form(self, f):
        fields = []
        for i in f.find_all(['input', 'textarea', 'select']):
            typ = i.get('type', 'text') if i.name == 'input' else i.name
            if typ == 'submit':
                continue
            fields.append({'tag': i.name, 'type': typ, 'name': i.get('name', ''), 'id': i.get('id', ''),
                           'placeholder': i.get('placeholder', ''), 'value': i.get('value', ''),
                           'required': i.has_attr('required') or '*' in (i.get('placeholder') or ''),
                           'options': [norm(o.get_text()) for o in i.find_all('option')] if i.name == 'select' else []})
        sub = f.find('input', type='submit') or f.find('button')
        msgs = [inline_html(p, self.page) for p in f.find_all('p')]
        labels = [text_of(l) for l in f.find_all('label') if text_of(l)]
        return {'t': 'form', 'name': f.get('name', ''), 'id': f.get('id', ''), 'action': f.get('action', ''),
                'enctype': f.get('enctype', ''), 'fields': fields,
                'submit': (sub.get('value') or text_of(sub)) if sub else 'Send', 'msgs': msgs, 'labels': labels}


def merge_blocks(blocks):
    """Group consecutive images into galleries, cards into grids, stats into rows, icon+caption into features."""
    out = []
    i = 0
    while i < len(blocks):
        b = blocks[i]
        if b['t'] == 'slider':
            b['slides'] = [merge_blocks(s) for s in b['slides']]
        # icon + short caption pattern
        if b['t'] == 'img' and i + 1 < len(blocks) and blocks[i + 1]['t'] == 'p' and len(re.sub('<[^>]+>', '', blocks[i + 1]['html'])) <= 140 \
                and i + 3 < len(blocks) and blocks[i + 2]['t'] == 'img' and blocks[i + 3]['t'] == 'p':
            feats = []
            while i + 1 < len(blocks) and blocks[i]['t'] == 'img' and blocks[i + 1]['t'] == 'p' and len(re.sub('<[^>]+>', '', blocks[i + 1]['html'])) <= 140:
                feats.append({'img': blocks[i]['src'], 'alt': blocks[i]['alt'], 'html': blocks[i + 1]['html']})
                i += 2
            out.append({'t': 'features', 'items': feats})
            continue
        for kind, group in (('img', 'gallery'), ('card', 'cards'), ('stat', 'stats'), ('video', 'videos')):
            if b['t'] == kind:
                j = i
                while j < len(blocks) and blocks[j]['t'] == kind: j += 1
                if j - i >= 2 or kind in ('card', 'stat'):
                    out.append({'t': group, 'items': blocks[i:j]})
                    i = j
                    break
        else:
            out.append(b)
            i += 1
            continue
    return out


def page_meta(s):
    title = norm(s.title.get_text()) if s.title else ''
    desc = ''
    m = s.find('meta', attrs={'name': 'description'})
    if m: desc = norm(m.get('content', ''))
    kw = s.find('meta', attrs={'name': 'keywords'})
    og = s.find('meta', attrs={'property': 'og:image'})
    can = s.find('link', rel='canonical')
    return {'title': title, 'description': desc, 'keywords': norm(kw.get('content', '')) if kw else '',
            'og_image': og.get('content', '') if og else '', 'canonical': can.get('href', '') if can else ''}


def classify(u):
    p = urllib.parse.urlparse(u).path
    if p in ('', '/'): return 'home'
    if re.match(r'^/work/[^/]+/\d+/', p): return 'work-detail'
    if p == '/work': return 'work'
    if re.match(r'^/work/[^/]+$', p): return 'work-cat'
    if p == '/clients': return 'clients'
    if re.match(r'^/clients/(current|past)-clients(/[a-z\-]+)?$', p):
        tail = p.split('/')[-1]
        sectors = {'automotive', 'beauty-and-cosmetics', 'education', 'energy-and-utilities', 'events', 'finance-and-fintech', 'fmcg',
                   'food-and-beverage', 'governmental-and-non-profit', 'healthcare', 'hospitality-and-tourism', 'ngos-and-igos',
                   'realestate', 'retail-and-e-commerce', 'shipping-and-transport', 'sports-and-e-sports', 'tech-media-and-telecom'}
        if tail.endswith('-clients') or tail in sectors: return 'clients-filter'
        return 'junk'
    if re.match(r'^/clients/\d+/', p): return 'junk'
    if re.match(r'^/blog/\d+/', p): return 'blog-detail'
    if p == '/blog': return 'blog'
    if p == '/news': return 'news'
    if re.match(r'^/\d+/', p): return 'junk'
    if p.startswith('/favicon'): return 'junk'
    return 'page'


def extract(u):
    html = load(u)
    s = BeautifulSoup(html, 'lxml')
    meta = page_meta(s)
    body = s.body
    sections = []
    hero = None
    for top in body.find_all(recursive=False):
        if not isinstance(top, Tag): continue
        cl = classes(top)
        if top.name in ('nav', 'footer', 'script', 'link', 'noscript', 'style'): continue
        if top.get('id') == 'fb-root' or 'fb-customerchat' in cl or 'overlay' in cl: continue
        if 'hero-slider' in cl:
            slides = []
            for sl in top.select('.swiper-slide'):
                w = Walker(u); bl = []; w.walk(sl, bl)
                slides.append(bl)
            sections.append({'cls': 'hero-slider', 'blocks': [{'t': 'heroslider', 'slides': slides}]})
            continue
        w = Walker(u)
        blocks = []
        # breadcrumb
        bc = top.select_one('ul.brdcrumb')
        crumbs = []
        if bc:
            for li in bc.find_all('li'):
                a = li.find('a')
                crumbs.append({'text': text_of(li), 'href': absu(a.get('href'), u) if a and a.get('href') not in ('#', None) else ''})
        if 'work-popup' in cl:
            continue
        w.node(top, blocks) if top.name not in ('section', 'div') else w.walk(top, blocks)
        if not blocks and not crumbs: continue
        sec = {'cls': ' '.join(cl), 'id': top.get('id', ''), 'blocks': merge_blocks(blocks)}
        if crumbs: sec['crumbs'] = crumbs
        if 'mfp-hide' in cl: sec['popup'] = top.get('id', '')
        bg = top.get('style', '')
        m = re.search(r'url\(([^)]+)\)', bg)
        if m: sec['bg'] = absu_img(m.group(1).strip('\'"'), u)
        sections.append(sec)
    # popups inside sections (e.g. careers forms)
    return {'url': u, 'path': urllib.parse.urlparse(u).path or '/', 'type': classify(u), 'meta': meta,
            'sections': sections}


def main():
    pages = []
    for u, v in IDX.items():
        if 'file' not in v: continue
        typ = classify(u)
        if typ == 'junk':
            pages.append({'url': u, 'path': urllib.parse.urlparse(u).path, 'type': 'junk'})
            continue
        try:
            pages.append(extract(u))
        except Exception as e:
            print('ERR', u, e); raise
    json.dump(pages, open(os.path.join(AUD, 'content.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    import collections
    print(collections.Counter(p['type'] for p in pages))


if __name__ == '__main__':
    main()
