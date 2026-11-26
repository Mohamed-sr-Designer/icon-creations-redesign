"""Render the redesigned ICON Creations site into docs/ from _audit/content.json.

Every text string comes verbatim from the extracted content; every image/video is the original asset
(mirrored under docs/ at its original path, plus a WebP derivative under docs/_opt/ for speed).
"""
import json, os, re, html, urllib.parse, shutil, sys
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract import load, norm, IDX

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, 'docs')
AUD = os.path.join(ROOT, '_audit')
P = json.load(open(os.path.join(AUD, 'content.json'), encoding='utf-8'))
MEDIA = json.load(open(os.path.join(AUD, 'media.json'), encoding='utf-8'))
DIMS = json.load(open(os.path.join(AUD, 'dims.json'), encoding='utf-8'))
BASE = 'https://icon-creations.com'
HOSTS = ('icon-creations.com', 'www.icon-creations.com')
BAD = '|?*"<>:'

SECTORS = [('automotive', 'Automotive'), ('beauty-and-cosmetics', 'Beauty & Cosmetics'), ('education', 'Education'),
           ('energy-and-utilities', 'Energy & Utilities'), ('events', 'Events'), ('finance-and-fintech', 'Finance & Fintech'),
           ('fmcg', 'FMCG'), ('food-and-beverage', 'Food & Beverage'), ('governmental-and-non-profit', 'Governmental & Non-Profit'),
           ('healthcare', 'Healthcare'), ('hospitality-and-tourism', 'Hospitality & Tourism'), ('ngos-and-igos', 'NGOs & IGOs'),
           ('realestate', 'Real Estate'), ('retail-and-e-commerce', 'Retail & E-Commerce'), ('shipping-and-transport', 'Shipping & Transport'),
           ('sports-and-e-sports', 'Sports & E-Sports'), ('tech-media-and-telecom', 'Tech, Media & Telecom')]

NAV = [('Home', '/'), ('About Us', '/about-us'), ('What We Do', '/what-we-do'), ('Work', '/work'), ('Clients', '/clients'),
       ('Sustainability', '/sustainability'), ('News', '/news'), ('Blog', '/blog'), ('Careers', '/careers'), ('Contact Us', '/contact-us')]
SOCIAL = [('Facebook', 'http://www.facebook.com/IconCreationsDigitalAgency'), ('Instagram', 'https://www.instagram.com/icon_creations'),
          ('LinkedIn', 'https://www.linkedin.com/company/icon-creations'), ('TikTok', 'https://www.tiktok.com/@icon_creations'),
          ('YouTube', 'https://www.youtube.com/channel/UCwp7MZ8vWReaZvvZQyXDIPw'), ('Behance', 'https://www.behance.net/IconCreations'),
          ('Vimeo', 'https://vimeo.com/iconcreations')]
WWD_ANCHORS = {'Digital Strategy': 'digital-strategy', 'Innovation & Experience Design': 'innovation',
               'Media Planning & Buying': 'media-planning', 'Social Media Management & Content Creation': 'social-media',
               'Video Production': 'video-production', 'Web & Mobile Intelligent Technology': 'web-mobile-technology',
               'Web Design & Development': 'web-mobile-technology'}

esc = lambda s: html.escape(s or '', quote=True)


# ---------------------------------------------------------------- paths & links
def clean_path(p):
    p = urllib.parse.unquote(p or '/')
    if len(p) > 1: p = p.rstrip('/')
    return p or '/'


def out_rel(p):
    """original path -> output folder (posix, relative to docs, '' for home)"""
    p = clean_path(p)
    segs = [s for s in p.split('/') if s]
    segs = [''.join('-' if ch in BAD else ch for ch in s) for s in segs]
    return '/'.join(segs)


PAGES = {clean_path(p['path']): p for p in P}
REDIRECTS = {}  # original path -> target original path


def junk_target(p):
    m = re.match(r'^/(\d+)/(.+)$', p)
    if m: return f'/blog/{m.group(1)}/{m.group(2)}'
    m = re.match(r'^/clients/(\d+)/([a-z\-]+)$', p)
    if m: return f'/clients/current-clients/{m.group(2)}'
    m = re.match(r'^/clients/(current|past)-clients/.+$', p)
    if m: return f'/clients/{m.group(1)}-clients'
    return '/clients'


for p in P:
    if p['type'] == 'junk':
        REDIRECTS[clean_path(p['path'])] = junk_target(clean_path(p['path']))


def rel_from(cur, target_rel, frag=''):
    """relative href from page folder `cur` to folder `target_rel` (both posix, relative to docs)"""
    a = [s for s in cur.split('/') if s]
    b = [s for s in target_rel.split('/') if s]
    i = 0
    while i < len(a) and i < len(b) and a[i] == b[i]: i += 1
    up = ['..'] * (len(a) - i)
    rest = [urllib.parse.quote(s, safe="-_.~()!'&,+") for s in b[i:]]
    r = '/'.join(up + rest)
    r = (r + '/') if rest else (r + '/' if r else './')
    return r + (('#' + frag) if frag else '')


class Ctx:
    def __init__(self, page_path):
        self.path = clean_path(page_path)
        self.rel = out_rel(self.path)

    def link(self, href):
        if not href: return '#'
        href = href.strip()
        if href.startswith(('mailto:', 'tel:', '#', 'javascript:')): return href
        u = urllib.parse.urlparse(href)
        if u.netloc and u.netloc not in HOSTS: return href
        p = clean_path(u.path)
        frag = u.fragment
        if p in REDIRECTS: p = REDIRECTS[p]
        if p in PAGES and PAGES[p]['type'] != 'junk':
            return rel_from(self.rel, out_rel(p), frag)
        full = BASE + urllib.parse.quote(urllib.parse.unquote(u.path))
        if full in MEDIA and MEDIA[full][0] == 'ok':
            return self.media(full)
        return BASE + u.path + (('?' + u.query) if u.query else '') + (('#' + frag) if frag else '')

    def asset(self, rel):
        return rel_from(self.rel, '').rstrip('/') + '/' + rel if self.rel else rel

    def media_rel(self, url):
        path = urllib.parse.unquote(urllib.parse.urlparse(url).path).lstrip('/')
        return path

    def media(self, url, opt=False):
        path = self.media_rel(url)
        if opt: path = '_opt/' + path + '.webp'
        up = '../' * len([s for s in self.rel.split('/') if s])
        return up + '/'.join(urllib.parse.quote(s) for s in path.split('/'))

    def rewrite_html(self, h):
        return re.sub(r'href="([^"]*)"', lambda m: f'href="{esc(self.link(html.unescape(m.group(1))))}"', h)


def ok(url):
    return bool(url) and not url.endswith('/') and MEDIA.get(url, ('missing',))[0] == 'ok'


def has_webp(url):
    path = urllib.parse.unquote(urllib.parse.urlparse(url).path).lstrip('/')
    return os.path.exists(os.path.join(DOCS, '_opt', *path.split('/'))) if False else os.path.exists(os.path.join(DOCS, '_opt', *(path + '.webp').split('/')))


def dims(url):
    path = urllib.parse.unquote(urllib.parse.urlparse(url).path).lstrip('/')
    return DIMS.get(path)


def pic(c, src, alt='', cls='', tablet='', mobile='', eager=False, sizes='100vw'):
    if src and src.startswith('http') and urllib.parse.urlparse(src).netloc not in HOSTS:
        return f'<picture class="{cls}"><img src="{esc(src)}" alt="{esc(alt)}" loading="lazy" decoding="async"></picture>'
    if not ok(src):
        for alt_src in (tablet, mobile):
            if ok(alt_src): src = alt_src; break
        else:
            return ''
    srcs = []
    if mobile and ok(mobile) and mobile != src:
        if has_webp(mobile): srcs.append(f'<source media="(max-width: 767px)" srcset="{c.media(mobile, True)}" type="image/webp">')
        srcs.append(f'<source media="(max-width: 767px)" srcset="{c.media(mobile)}">')
    if tablet and ok(tablet) and tablet != src:
        if has_webp(tablet): srcs.append(f'<source media="(max-width: 1199px)" srcset="{c.media(tablet, True)}" type="image/webp">')
        srcs.append(f'<source media="(max-width: 1199px)" srcset="{c.media(tablet)}">')
    if has_webp(src):
        srcs.append(f'<source srcset="{c.media(src, True)}" type="image/webp">')
    d = dims(src)
    wh = f' width="{d[0]}" height="{d[1]}"' if d else ''
    load_attr = 'eager" fetchpriority="high' if eager else 'lazy'
    return (f'<picture class="{cls}">' + ''.join(srcs) +
            f'<img src="{c.media(src)}" alt="{esc(alt)}"{wh} loading="{load_attr}" decoding="async"></picture>')


# ---------------------------------------------------------------- block renderer
ARROW = '<svg class="ico" viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6" fill="none" stroke="currentColor" stroke-width="1.6"/></svg>'
PLAY = '<svg class="ico" viewBox="0 0 24 24" aria-hidden="true"><path d="M8 5v14l11-7z" fill="currentColor"/></svg>'


def heading(c, b, lvl_override=None, cls=''):
    lvl = lvl_override or b['lvl']
    lvl = max(2, min(lvl, 6)) if lvl_override is None and b['lvl'] == 1 and False else lvl
    eb = f'<span class="eyebrow">{esc(b["eyebrow"])}</span> ' if b.get('eyebrow') else ''
    inner = c.rewrite_html(b['html'])
    inner = re.sub(r'^\s*<br>\s*', '', inner)
    ar = ' lang="ar" dir="rtl"' if b.get('ar') else ''
    size = {1: 'h-xl', 2: 'h-l', 3: 'h-m', 4: 'h-s', 5: 'h-xs', 6: 'h-xs'}[b['lvl']]
    return f'<h{lvl} class="{size} {cls}"{ar}>{eb}<span class="ht">{inner}</span></h{lvl}>'


def video_embed(b):
    src = b['src'].strip()
    if b.get('kind') == 'file':
        return f'<div class="vid"><video controls preload="metadata" playsinline src="{esc(src)}">{esc(b.get("fallback", ""))}</video></div>'
    yt = re.search(r'youtube\.com/embed/([\w\-]+)', src)
    if yt:
        vid = yt.group(1)
        return (f'<div class="vid vid-yt" data-src="{esc(src)}"><button class="vid-play" type="button" aria-label="Play video">'
                f'<img src="https://i.ytimg.com/vi/{vid}/hqdefault.jpg" alt="" loading="lazy">{PLAY}</button></div>')
    return f'<div class="vid"><iframe src="{esc(src)}" loading="lazy" allowfullscreen allow="autoplay; encrypted-media; picture-in-picture" title="Video"></iframe></div>'


def render_blocks(c, blocks, ctx=None):
    out = []
    for b in blocks:
        t = b['t']
        if t == 'anchor':
            continue
        if t == 'h':
            out.append(heading(c, b))
        elif t == 'p':
            hid = ' hidden' if b.get('hidden') else ''
            out.append(f'<p class="txt"{hid}>{c.rewrite_html(b["html"])}</p>')
        elif t == 'label':
            out.append(f'<p class="tag">{esc(b["text"])}</p>')
        elif t == 'img':
            im = pic(c, b['src'], b.get('alt', ''), 'media', b.get('tablet', ''), b.get('mobile', ''))
            if b.get('href'): im = f'<a href="{esc(c.link(b["href"]))}" class="media-link">{im}</a>'
            if im: out.append(f'<figure class="fig">{im}</figure>')
        elif t == 'gallery':
            items = []
            for it in b['items']:
                im = pic(c, it['src'], it.get('alt', ''), 'media', it.get('tablet', ''), it.get('mobile', ''), sizes='(min-width: 900px) 33vw, 100vw')
                if not im: continue
                if it.get('href'):
                    items.append(f'<a class="g-item" href="{esc(c.link(it["href"]))}">{im}</a>')
                else:
                    items.append(f'<button class="g-item" type="button" data-lightbox="{c.media(it["src"])}" aria-label="Open image">{im}</button>')
            n = len(items)
            out.append(f'<div class="gallery g-{min(n, 4)}" data-count="{n}">' + ''.join(items) + '</div>')
        elif t == 'cards':
            out.append(render_cards(c, b['items']))
        elif t == 'stats':
            out.append('<div class="stats">' + ''.join(
                f'<div class="stat"><p class="stat-n"><span class="num" data-count="{esc(s["num"])}">{esc(s["num"])}</span><span class="suf">{esc(s["suffix"])}</span></p>'
                f'<p class="stat-l">{c.rewrite_html(s["label"])}</p></div>' for s in b['items']) + '</div>')
        elif t == 'features':
            out.append('<div class="features">' + ''.join(
                f'<div class="feat">{pic(c, f["img"], f.get("alt", ""), "feat-ico")}<p>{c.rewrite_html(f["html"])}</p></div>'
                for f in b['items']) + '</div>')
        elif t == 'list':
            tag = 'ol' if b.get('ordered') else 'ul'
            out.append(f'<{tag} class="lst">' + ''.join(f'<li>{c.rewrite_html(i)}</li>' for i in b['items']) + f'</{tag}>')
        elif t == 'btn':
            if b.get('popup'):
                out.append(f'<button class="btn" type="button" data-dialog="{esc(b["popup"][1:])}">{esc(b["text"])}{ARROW}</button>')
            else:
                href = c.link(b['href'])
                ext = ' target="_blank" rel="noopener"' if href.startswith('http') else ''
                out.append(f'<a class="btn" href="{esc(href)}"{ext}>{esc(b["text"])}{ARROW}</a>')
        elif t == 'video':
            out.append(video_embed(b))
        elif t == 'videos':
            out.append('<div class="videos">' + ''.join(video_embed(v) for v in b['items']) + '</div>')
        elif t == 'slider':
            out.append(render_rail(c, b['slides']))
        elif t == 'map':
            out.append(f'<div class="map"><iframe src="{esc(b["src"])}" loading="lazy" title="Icon Creations on Google Maps" referrerpolicy="no-referrer-when-downgrade">{esc(b.get("text", ""))}</iframe></div>')
        elif t == 'form':
            out.append(render_form(c, b))
        elif t == 'share':
            label = {'fb': 'Facebook', 'lin': 'LinkedIn', 'tw': 'Twitter'}.get(b['net'], b['net'])
            out.append(f'<a class="share" href="{esc(b["href"])}" target="_blank" rel="noopener" aria-label="Share on {label}">{label}</a>')
        elif t == 'table':
            out.append(f'<div class="table">{b["html"]}</div>')
    return ''.join(out)


def render_cards(c, items, cls='cards'):
    out = []
    for i, it in enumerate(items):
        im = pic(c, it['img'], it.get('alt', ''), 'card-img', sizes='(min-width: 900px) 33vw, 100vw')
        icon = pic(c, it['icon'], it.get('icon_alt', ''), 'card-icon') if it.get('icon') else ''
        meta = f'<span class="card-meta">{esc(it["meta"])}</span>' if it.get('meta') else ''
        title = c.rewrite_html(it['title']) if '<' in it['title'] else esc(it['title'])
        out.append(f'<a class="card reveal" href="{esc(c.link(it["href"]))}" style="--i:{i % 6}">'
                   f'<span class="card-media">{im}<span class="dotveil" aria-hidden="true"></span></span>'
                   f'<span class="card-body">{icon}<span class="card-title">{title}</span>{meta}</span></a>')
    return f'<div class="{cls}">' + ''.join(out) + '</div>'


def render_rail(c, slides, cls=''):
    items = ''.join(f'<div class="rail-item">{render_blocks(c, s)}</div>' for s in slides)
    n = len(slides)
    return (f'<div class="rail {cls}" data-rail><div class="rail-track" tabindex="0">{items}</div>'
            f'<div class="rail-ctl"><span class="rail-count"><b>01</b> / {n:02d}</span>'
            f'<button type="button" class="rail-btn" data-dir="-1" aria-label="Previous">{ARROW}</button>'
            f'<button type="button" class="rail-btn" data-dir="1" aria-label="Next">{ARROW}</button></div></div>')


def render_form(c, b):
    contact = b.get('name') == 'coolform'
    fields = []
    for f in b['fields']:
        ph = f['placeholder']
        nm = f['name'] or f['id']
        req = ' required' if f.get('required') else ''
        if f['type'] == 'hidden':
            fields.append(f'<input type="hidden" name="{esc(nm)}" value="{esc(f["value"])}">'); continue
        if f['tag'] == 'textarea':
            ctrl = f'<textarea name="{esc(nm)}" rows="4" placeholder=" "{req}></textarea>'
        elif f['tag'] == 'select':
            ctrl = f'<select name="{esc(nm)}"{req}>' + ''.join(f'<option>{esc(o)}</option>' for o in f['options']) + '</select>'
        else:
            typ = 'tel' if f['type'] == 'number' else f['type']
            ctrl = f'<input type="{esc(typ)}" name="{esc(nm)}" placeholder=" " autocomplete="on"{req}>'
        wide = ' wide' if f['tag'] == 'textarea' else ''
        fields.append(f'<label class="fld{wide}">{ctrl}<span>{esc(ph)}</span></label>')
    msgs = b.get('msgs', [])
    note = f'<p class="form-note">{c.rewrite_html(msgs[0])}</p>' if msgs else ''
    thanks = f'<p class="form-ok" hidden>{c.rewrite_html(msgs[1])}</p>' if len(msgs) > 1 else ''
    action = 'https://icon-creations.com/contact-us/ajaxsubmit.php' if contact else (b.get('action') if b.get('action') not in ('', '#') else '')
    return (f'<form class="form" method="post" data-ajax="{esc(action)}" novalidate>'
            f'<div class="form-grid">{"".join(fields)}</div>{note}'
            f'<button class="btn btn-solid" type="submit">{esc(b["submit"])}{ARROW}</button>'
            f'<p class="form-err" role="alert" hidden></p>{thanks}</form>')


# ---------------------------------------------------------------- sections
def hero_from(c, sec, kind='page', extra_title=''):
    """top-banner section -> cinematic hero"""
    blocks = sec['blocks']
    flat = []
    for b in blocks:
        if b['t'] == 'gallery': flat += b['items']
        else: flat.append(b)
    imgs = [b for b in flat if b['t'] == 'img']
    rest = [b for b in flat if b['t'] != 'img' and b['t'] != 'anchor']
    banner = imgs[0] if imgs else None
    logo = imgs[1] if len(imgs) > 1 else None
    media = pic(c, banner['src'], banner.get('alt', ''), 'hero-img', banner.get('tablet', ''), banner.get('mobile', ''), eager=True) if banner else ''
    texts = []
    for b in rest:
        if b['t'] == 'h':
            texts.append(heading(c, b, lvl_override=1, cls='hero-title'))
        elif b['t'] == 'p':
            texts.append(f'<p class="hero-lede">{c.rewrite_html(b["html"])}</p>')
        else:
            texts.append(render_blocks(c, [b]))
    logo_html = f'<div class="hero-logo">{pic(c, logo["src"], logo.get("alt", ""), "", eager=True)}</div>' if logo else ''
    return (f'<header class="hero hero-{kind}"><div class="hero-media">{media}</div><div class="hero-scrim"></div>'
            f'<div class="hero-inner wrap">{logo_html}{"".join(texts)}</div>'
            f'<div class="hero-index" aria-hidden="true"><span></span></div></header>')


def crumbs_html(c, crumbs):
    if not crumbs: return ''
    lis = []
    for i, cr in enumerate(crumbs):
        if cr['href'] and i < len(crumbs) - 1:
            lis.append(f'<li><a href="{esc(c.link(cr["href"]))}">{esc(cr["text"])}</a></li>')
        else:
            lis.append(f'<li aria-current="page">{esc(cr["text"])}</li>')
    return f'<nav class="crumbs wrap" aria-label="Breadcrumb"><ol>{"".join(lis)}</ol></nav>'


WIDE = {'gallery', 'cards', 'stats', 'features', 'slider', 'videos', 'map', 'form', 'table'}


def section_html(c, sec, idx, tone=None):
    blocks = [b for b in sec['blocks'] if b['t'] != 'anchor']
    if not blocks:
        return crumbs_html(c, sec.get('crumbs'))
    cls = sec.get('cls', '')
    tone = tone or ('ink' if any(k in cls for k in ('bg-darkblue', 'social-results', 'work-dtls-sec2 bg', 'work-video')) else 'paper')
    imgs = [b for b in blocks if b['t'] == 'img']
    wide = [b for b in blocks if b['t'] in WIDE]
    texty = [b for b in blocks if b['t'] in ('h', 'p', 'btn', 'list', 'label', 'share')]
    bg = ''
    if sec.get('bg') and ok(sec['bg']):
        bg = f'<div class="sec-bg">{pic(c, sec["bg"], "", "")}</div>'
    head = crumbs_html(c, sec.get('crumbs'))
    if len(imgs) == 1 and not wide and texty:
        # editorial split: text column + media column
        i_img = blocks.index(imgs[0])
        txt = render_blocks(c, [b for b in blocks if b is not imgs[0]])
        med = render_blocks(c, [imgs[0]])
        flip = ' flip' if i_img < len(blocks) // 2 else ''
        body = f'<div class="split{flip}"><div class="split-txt">{txt}</div><div class="split-media reveal">{med}</div></div>'
    else:
        # flow: group consecutive text into readable columns, wide blocks full width
        parts, buf = [], []
        def flush():
            if buf:
                parts.append(f'<div class="flow">{render_blocks(c, buf)}</div>'); buf.clear()
        for b in blocks:
            if b['t'] in WIDE or b['t'] == 'video' or b['t'] == 'img':
                flush(); parts.append(f'<div class="wide reveal">{render_blocks(c, [b])}</div>')
            else:
                buf.append(b)
        flush()
        body = ''.join(parts)
    sid = f' id="{esc(sec["id"])}"' if sec.get('id') and not sec['id'].startswith('popup') else ''
    num = f'<span class="sec-num" aria-hidden="true">{idx:02d}</span>'
    return f'{head}<section class="sec tone-{tone}"{sid}>{bg}<div class="wrap">{num}{body}</div></section>'


def popup_html(c, sec):
    pid = sec['popup']
    body = render_blocks(c, sec['blocks'])
    return (f'<dialog class="modal" id="{esc(pid)}" aria-label="Details"><div class="modal-in">'
            f'<button class="modal-x" type="button" data-close aria-label="Close">Close</button>{body}</div></dialog>')


def generic_sections(c, page, start=0, hero_kind='page'):
    secs = page['sections']
    out, popups = [], []
    idx = 1
    for i, s in enumerate(secs):
        if i < start: continue
        if s.get('popup'):
            popups.append(popup_html(c, s)); continue
        if 'top-banner' in s.get('cls', '') and i <= 1:
            out.append(hero_from(c, s, hero_kind)); continue
        out.append(section_html(c, s, idx)); idx += 1
    return ''.join(out) + ''.join(popups)


# ---------------------------------------------------------------- shell
def shell(c, page, body, body_cls=''):
    m = page.get('meta', {})
    title = m.get('title') or 'Icon Creations'
    desc = m.get('description', '')
    canon = BASE + urllib.parse.quote(clean_path(page['path'])) if page['path'] not in ('', '/') else BASE + '/'
    cur = c.path
    nav_items = []
    for i, (label, p) in enumerate(NAV, 1):
        active = (p == '/' and cur == '/') or (p != '/' and (cur == p or cur.startswith(p + '/')))
        ac = ' aria-current="page"' if active else ''
        nav_items.append(f'<li><a href="{esc(c.link(BASE + p))}"{ac}><span class="n">{i:02d}</span><span class="l">{esc(label)}</span></a></li>')
    social = ''.join(f'<a href="{esc(u)}" target="_blank" rel="noopener">{esc(n)}</a>' for n, u in SOCIAL)
    logo_w = c.media(BASE + '/images/icon-creations-logo-white.png')
    css = c.asset('assets/site.css')
    js = c.asset('assets/site.js')
    og = m.get('og_image') or BASE + '/images/logo300.jpg'
    kw = f'<meta name="keywords" content="{esc(m["keywords"])}">' if m.get('keywords') else ''
    return f'''<!doctype html>
<html lang="en" class="no-js">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
{kw}
<link rel="canonical" href="{esc(canon)}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:image" content="{esc(og)}">
<meta property="og:type" content="website">
<meta name="theme-color" content="#0b0c0e">
<link rel="icon" href="{c.media(BASE + '/favicon/favicon-32x32.png')}" sizes="32x32">
<link rel="apple-touch-icon" href="{c.media(BASE + '/favicon/apple-touch-icon.png')}">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,300..900&family=Instrument+Serif:ital@0;1&family=IBM+Plex+Sans+Arabic:wght@400;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{css}">
</head>
<body class="{body_cls}">
<a class="skip" href="#main">Skip to content</a>
<div class="bar" data-bar>
  <a class="bar-logo" href="{esc(c.link(BASE + '/'))}" aria-label="Icon Creations home"><img src="{logo_w}" alt="Logo" width="147" height="46"></a>
  <div class="bar-right">
    <a class="bar-cta" href="{esc(c.link(BASE + '/contact-us'))}">Contact Us</a>
    <button class="bar-menu" type="button" aria-expanded="false" aria-controls="menu" data-menu><span class="bar-menu-dots" aria-hidden="true"><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i></span><span class="bar-menu-l">Menu</span></button>
  </div>
</div>
<div class="menu" id="menu" hidden>
  <div class="menu-in wrap">
    <nav aria-label="Main"><ol class="menu-list">{''.join(nav_items)}</ol></nav>
    <aside class="menu-aside">
      <p class="menu-k">Contact us</p>
      <p>28 Street 7, Maadi, Cairo, Egypt</p>
      <p><a href="mailto:info@icon-creations.com">info@icon-creations.com</a></p>
      <p><a href="tel:+201222124808">+201222124808</a></p>
      <p><a href="https://wa.me/201222124808" target="_blank" rel="noopener">+20 122 212 4808</a></p>
      <p class="menu-k">stay connected</p>
      <div class="menu-social">{social}</div>
    </aside>
  </div>
</div>
<main id="main">
{body}
</main>
{footer(c)}
<dialog class="lightbox" id="lightbox" aria-label="Image viewer"><img alt=""><button type="button" class="lb-x" data-close aria-label="Close">Close</button><button type="button" class="lb-prev" aria-label="Previous image">{ARROW}</button><button type="button" class="lb-next" aria-label="Next image">{ARROW}</button></dialog>
<script src="{js}" defer></script>
</body>
</html>'''


def footer(c):
    links = [('About us', '/about-us'), ('What we do', '/what-we-do'), ('Work', '/work'), ('Clients', '/clients'),
             ('Sustainability', '/sustainability'), ('News', '/news'), ('Blog', '/blog'), ('Contact us', '/contact-us'), ('Careers', '/careers')]
    li = ''.join(f'<li><a href="{esc(c.link(BASE + p))}">{esc(t)}</a></li>' for t, p in links)
    social = ''.join(f'<a href="{esc(u)}" target="_blank" rel="noopener">{esc(n)}</a>' for n, u in SOCIAL)
    logo_w = c.media(BASE + '/images/icon-creations-logo-white.png')
    return f'''<footer class="foot">
  <div class="wrap foot-grid">
    <div class="foot-brand">
      <a href="{esc(c.link(BASE + '/'))}"><img src="{logo_w}" alt="Logo" width="147" height="46" loading="lazy"></a>
      <p>A rapidly evolving digital agency in Egypt with more than 23 years of digital experience.</p>
    </div>
    <nav class="foot-nav" aria-label="Footer"><ul>{li}</ul></nav>
    <div class="foot-contact">
      <h2 class="foot-k">Contact us</h2>
      <p>28 Street 7, Maadi, Cairo, Egypt</p>
      <p><a href="mailto:info@icon-creations.com">info@icon-creations.com</a></p>
      <p><a href="tel:+201222124808">+201222124808</a></p>
      <p><a class="wa" href="https://wa.me/201222124808" target="_blank" rel="noopener">+20 122 212 4808</a></p>
    </div>
    <div class="foot-news">
      <h2 class="foot-k">stay connected</h2>
      <p>Enter your email address below to receive our latest newsletter. </p>
      <form class="news-form" data-ajax="https://icon-creations.com/ajaxsubmit.php" novalidate>
        <label class="fld"><input type="email" name="email" placeholder=" " required><span>E-mail</span></label>
        <button class="btn btn-solid" type="submit">Subscribe{ARROW}</button>
        <p class="form-err" role="alert" hidden></p>
      </form>
    </div>
  </div>
  <div class="wrap foot-base">
    <div class="foot-social">{social}</div>
    <small>© Icon Creations 2003-2026 <br> All Rights Reserved</small>
  </div>
  <div class="foot-mark" aria-hidden="true"><span>icon</span><i class="dotfield"></i></div>
</footer>'''


# ---------------------------------------------------------------- page types
def raw_soup(page):
    return BeautifulSoup(load(page['url']), 'lxml')


def page_home(page):
    c = Ctx('/')
    secs = {s['cls'].split()[0] if s['cls'] else '': s for s in page['sections']}
    # hero slider
    hs = page['sections'][0]['blocks'][0]['slides']
    slides = []
    for i, sl in enumerate(hs):
        img = next(b for b in sl if b['t'] == 'img')
        txt = ''.join(heading(c, b, lvl_override=1 if i == 0 else 2, cls='hero-title') if b['t'] == 'h' else
                      (f'<p class="hero-lede">{c.rewrite_html(b["html"])}</p>' if b['t'] == 'p' else '') for b in sl if b['t'] != 'img')
        cap = f'<p class="slide-cap"><span>{i + 1:02d}</span>{esc(img.get("alt", ""))}</p>'
        slides.append(f'<div class="slide{" is-on" if i == 0 else ""}" data-slide aria-roledescription="slide" aria-label="{i + 1} of {len(hs)}">'
                      f'<div class="hero-media">{pic(c, img["src"], img.get("alt", ""), "hero-img", img.get("tablet", ""), img.get("mobile", ""), eager=(i == 0))}</div>'
                      f'<div class="hero-scrim"></div><div class="hero-inner wrap">{txt}</div>{cap}</div>')
    dots = ''.join(f'<button type="button" class="hs-dot{" is-on" if i == 0 else ""}" aria-label="Show slide {i + 1}"><span></span></button>' for i in range(len(hs)))
    hero = (f'<header class="hero hero-home" data-heroslider aria-roledescription="carousel" aria-label="Featured work">{"".join(slides)}'
            f'<div class="hs-ctl wrap"><div class="hs-dots">{dots}</div><button type="button" class="hs-pause" aria-label="Pause slideshow" aria-pressed="false"><i></i><i></i></button></div>'
            f'<a class="hero-scroll" href="#who" aria-label="Scroll to content"><span></span></a></header>')

    about = page['sections'][1]['blocks']
    a_h = next(b for b in about if b['t'] == 'h'); a_p = next(b for b in about if b['t'] == 'p'); a_btn = next(b for b in about if b['t'] == 'btn')
    s_about = (f'<section class="sec tone-paper home-who" id="who"><div class="wrap"><span class="sec-num">01</span>'
               f'<div class="who-grid"><div>{heading(c, a_h, cls="display")}</div><div class="who-txt"><p class="lede">{c.rewrite_html(a_p["html"])}</p>{render_blocks(c, [a_btn])}</div></div></div></section>')

    sv = page['sections'][2]['blocks']
    sv_h = next(b for b in sv if b['t'] == 'h'); sv_ps = [b for b in sv if b['t'] == 'p']; sv_btn = next(b for b in sv if b['t'] == 'btn')
    cards = next(b for b in sv if b['t'] == 'cards')['items']
    svc = ''.join(f'<a class="svc reveal" style="--i:{i}" href="{esc(c.link(it["href"]))}"><span class="svc-n">{i + 1:02d}</span>'
                  f'<span class="svc-media">{pic(c, it["img"], it.get("alt", ""), "svc-img")}</span>'
                  f'<span class="svc-ico">{pic(c, it["icon"], it.get("icon_alt", ""), "")}</span>'
                  f'<span class="svc-t">{c.rewrite_html(it["title"])}</span>{ARROW}</a>' for i, it in enumerate(cards))
    s_services = (f'<section class="sec tone-ink home-svc"><div class="wrap"><span class="sec-num">02</span>'
                  f'<div class="svc-head">{heading(c, sv_h, cls="display")}<div><p class="kicker">{c.rewrite_html(sv_ps[0]["html"])}</p>'
                  f'<p class="lede">{c.rewrite_html(sv_ps[1]["html"])}</p>{render_blocks(c, [sv_btn])}</div></div>'
                  f'<div class="svc-list">{svc}</div></div></section>')

    wk = page['sections'][3]['blocks']
    wk_h = next(b for b in wk if b['t'] == 'h')
    tabs = next(b for b in wk if b['t'] == 'list')['items']
    tab_labels = [re.sub('<[^>]+>', '', t) for t in tabs]
    wcards = next(b for b in wk if b['t'] == 'cards')['items']
    wk_btn = next(b for b in wk if b['t'] == 'btn')
    tab_btns = ''.join(f'<button type="button" role="tab" class="chip" aria-selected="{"true" if i == 0 else "false"}" data-tab="{i}">{esc(l)}</button>' for i, l in enumerate(tab_labels))
    panes = ''
    for i in range(len(tab_labels)):
        grp = wcards[i * 3:(i + 1) * 3]
        panes += f'<div class="pane" role="tabpanel" data-pane="{i}"{"" if i == 0 else " hidden"}>{render_cards(c, grp, "cards cards-3")}</div>'
    s_work = (f'<section class="sec tone-paper home-work"><div class="wrap"><span class="sec-num">03</span>'
              f'<div class="work-head">{heading(c, wk_h, cls="display")}<div class="chips" role="tablist" aria-label="Work categories">{tab_btns}</div></div>'
              f'<div data-tabs>{panes}</div><div class="center">{render_blocks(c, [wk_btn])}</div></div></section>')

    news = page['sections'][4]['blocks'][0]['slides']
    n_items = []
    for i, sl in enumerate(news):
        hs_ = [b for b in sl if b['t'] == 'h']; ps = [b for b in sl if b['t'] == 'p']; btn = [b for b in sl if b['t'] == 'btn']
        imgs = [b for b in sl if b['t'] == 'img']
        n_items.append(f'<article class="news-card reveal" style="--i:{i}">'
                       + (f'<p class="news-k">{heading(c, hs_[0], lvl_override=3, cls="news-eyebrow")}</p>' if hs_ else '')
                       + (pic(c, imgs[0]['src'], imgs[0].get('alt', ''), 'news-img') if imgs else '')
                       + (f'<p class="news-date">{c.rewrite_html(ps[0]["html"])}</p>' if ps else '')
                       + (heading(c, hs_[1], lvl_override=3, cls='news-t') if len(hs_) > 1 else '')
                       + ''.join(f'<p class="txt">{c.rewrite_html(p["html"])}</p>' for p in ps[1:])
                       + render_blocks(c, btn) + '</article>')
    s_news = (f'<section class="sec tone-ink home-news"><div class="wrap"><span class="sec-num">04</span>'
              f'<div class="news-rail" data-rail><div class="rail-track" tabindex="0">{"".join(n_items)}</div>'
              f'<div class="rail-ctl"><span class="rail-count"><b>01</b> / {len(news):02d}</span>'
              f'<button type="button" class="rail-btn" data-dir="-1" aria-label="Previous">{ARROW}</button><button type="button" class="rail-btn" data-dir="1" aria-label="Next">{ARROW}</button></div></div></div></section>')

    ct = page['sections'][5]['blocks']
    mp = next(b for b in ct if b['t'] == 'map'); ch = next(b for b in ct if b['t'] == 'h'); cp = next(b for b in ct if b['t'] == 'p'); cf = next(b for b in ct if b['t'] == 'form')
    s_contact = (f'<section class="sec tone-paper home-contact"><div class="wrap"><span class="sec-num">05</span><div class="contact-grid">'
                 f'<div>{heading(c, ch, cls="display")}<p class="lede">{c.rewrite_html(cp["html"])}</p>{render_form(c, cf)}</div>'
                 f'<div class="contact-map">{render_blocks(c, [mp])}</div></div></div></section>')
    return shell(c, page, hero + s_about + s_services + s_work + s_news + s_contact, 'is-home')


def work_index_data():
    page = PAGES['/work']
    s = raw_soup(page)
    items = []
    for it in s.select('.work-grid .work-item'):
        a = it.find('a')
        img = a.find('img')
        items.append({'href': a.get('href'), 'img': urllib.parse.urljoin(BASE + '/work/', img.get('src')), 'alt': norm(img.get('alt', '')),
                      'title': norm(a.find('strong').get_text()), 'meta': norm(a.find('small').get_text()),
                      'latest': 'Latest-work' in it.get('class', [])})
    filters = [norm(x.get_text()) for x in s.select('.work-filter a')]
    return items, filters


def page_work(page):
    c = Ctx('/work')
    banner = page['sections'][0]['blocks'][0]
    slides = banner['slides'] if banner['t'] == 'slider' else []
    hero_slides = []
    for i, sl in enumerate(slides):
        img = next((b for b in sl if b['t'] == 'img'), None)
        txt = render_blocks(c, [b for b in sl if b['t'] != 'img']) if i == 0 else ''
        hero_slides.append(f'<div class="slide{" is-on" if i == 0 else ""}" data-slide><div class="hero-media">'
                           + (pic(c, img['src'], img.get('alt', ''), 'hero-img', img.get('tablet', ''), img.get('mobile', ''), eager=(i == 0)) if img else '') + '</div><div class="hero-scrim"></div>'
                           + '</div>')
    first_txt = [b for b in slides[0] if b['t'] != 'img'] if slides else []
    # keep every slide's text: slides share the same headline/paragraph; render once, verbatim, plus per-slide copies hidden from layout (sr-only) to preserve 1:1 content
    extra = ''.join(f'<div class="sr-only">{render_blocks(c, [b for b in sl if b["t"] != "img"])}</div>' for sl in slides[1:])
    t_h = next((b for b in first_txt if b['t'] == 'h'), None)
    t_p = next((b for b in first_txt if b['t'] == 'p'), None)
    dots = ''.join(f'<button type="button" class="hs-dot{" is-on" if i == 0 else ""}" aria-label="Show slide {i + 1}"><span></span></button>' for i in range(len(slides)))
    hero = (f'<header class="hero hero-work" data-heroslider>{"".join(hero_slides)}<div class="hero-inner wrap hero-fixed">'
            + (heading(c, t_h, lvl_override=1, cls='hero-title') if t_h else '') + (f'<p class="hero-lede">{c.rewrite_html(t_p["html"])}</p>' if t_p else '')
            + f'</div>{extra}<div class="hs-ctl wrap"><div class="hs-dots">{dots}</div><button type="button" class="hs-pause" aria-label="Pause slideshow" aria-pressed="false"><i></i><i></i></button></div></header>')
    items, filters = work_index_data()
    chips = ''.join(f'<button type="button" class="chip" aria-pressed="{"true" if i == 0 else "false"}" data-filter="{esc(f)}">{esc(f)}</button>' for i, f in enumerate(filters))
    grid = []
    for i, it in enumerate(items):
        cats = [x.strip() for x in it['meta'].split('/')]
        if it['latest'] and 'Latest' not in cats: cats.append('Latest')
        im = pic(c, it['img'], it['alt'], 'card-img', sizes='(min-width: 900px) 33vw, 100vw')
        grid.append(f'<a class="card reveal" style="--i:{i % 6}" href="{esc(c.link(it["href"]))}" data-cats="{esc("|".join(cats))}">'
                    f'<span class="card-media">{im}<span class="dotveil" aria-hidden="true"></span></span>'
                    f'<span class="card-body"><span class="card-no">{len(items) - i:03d}</span><span class="card-title">{esc(it["title"])}</span>'
                    f'<span class="card-meta">{esc(it["meta"])}</span></span></a>')
    body = (hero + f'<section class="sec tone-paper work-index"><div class="wrap">'
            f'<div class="filterbar"><div class="chips" role="group" aria-label="Filter work">{chips}</div><p class="count" aria-live="polite"><b data-count-out>{len(items)}</b> / {len(items)}</p></div>'
            f'<div class="cards cards-work" data-filter-grid>{"".join(grid)}</div></div></section>')
    return shell(c, page, body, 'is-work')


def page_work_detail(page):
    c = Ctx(page['path'])
    body = generic_sections(c, page, hero_kind='case')
    # prev / next through the work index order
    items, _ = work_index_data()
    hrefs = [clean_path(urllib.parse.urlparse(i['href']).path) for i in items]
    me = clean_path(page['path'])
    nav = ''
    if me in hrefs:
        k = hrefs.index(me)
        prv = items[k - 1] if k > 0 else items[-1]
        nxt = items[(k + 1) % len(items)]
        nav = (f'<nav class="pn wrap" aria-label="More projects"><a class="pn-a" href="{esc(c.link(prv["href"]))}"><span class="pn-k">←</span><span>{esc(prv["title"])}</span></a>'
               f'<a class="pn-a pn-next" href="{esc(c.link(nxt["href"]))}"><span>{esc(nxt["title"])}</span><span class="pn-k">→</span></a></nav>')
    return shell(c, page, body + nav, 'is-case')


def clients_data():
    """status -> sector -> [logo urls] from the 34 filter pages"""
    data = {}
    for p in P:
        if p['type'] != 'clients-filter': continue
        parts = clean_path(p['path']).split('/')
        status = parts[2].replace('-clients', '')
        sector = parts[3] if len(parts) > 3 else 'all'
        logos = []
        def walk(o):
            if isinstance(o, dict):
                if o.get('t') == 'img' and '/uploads/clients/' in o.get('src', ''): logos.append(o['src'])
                for v in o.values(): walk(v)
            elif isinstance(o, list):
                for x in o: walk(x)
        walk(p['sections'])
        data.setdefault(status, {})[sector] = logos
    return data


def page_clients(page, status='current', sector='all'):
    c = Ctx(page['path'])
    top = page['sections'][0]
    hero = hero_from(c, top)
    data = clients_data()
    logos = {}
    for st, secs in data.items():
        for sec, lst in secs.items():
            for i, u in enumerate(lst):
                e = logos.setdefault(u, {'st': set(), 'sec': set(), 'order': {}})
                e['st'].add(st)
                if sec != 'all': e['sec'].add(sec)
                if sec == 'all': e['order'][st] = i
                else: e['order'].setdefault(st + '_s', 1000 + i)
    items = []
    for u, e in logos.items():
        name = re.sub(r'^\d+_', '', urllib.parse.unquote(u.rsplit('/', 1)[-1]).rsplit('.', 1)[0])
        items.append((e, f'<li class="logo" data-st="{" ".join(sorted(e["st"]))}" data-sec="{" ".join(sorted(e["sec"]))}" '
                         f'data-o-current="{e["order"].get("current", e["order"].get("current_s", 9999))}" data-o-past="{e["order"].get("past", e["order"].get("past_s", 9999))}">'
                         f'{pic(c, u, "", "")}<span class="sr-only">{esc(name)}</span></li>'))
    items.sort(key=lambda x: (x[0]['order'].get(status, x[0]['order'].get(status + '_s', 9999))))
    st_btn = ''.join(f'<a class="chip" href="{esc(c.link(BASE + f"/clients/{k}-clients" + ("/" + sector if sector != "all" else "")))}" data-st="{k}" aria-pressed="{"true" if k == status else "false"}">{lbl}</a>'
                     for k, lbl in (('current', 'Current Clients'), ('past', 'Past Clients')))
    sec_btn = f'<a class="chip" data-sec="all" href="{esc(c.link(BASE + f"/clients/{status}-clients"))}" aria-pressed="{"true" if sector == "all" else "false"}">All</a>' + ''.join(
        f'<a class="chip" data-sec="{k}" href="{esc(c.link(BASE + f"/clients/{status}-clients/{k}"))}" aria-pressed="{"true" if sector == k else "false"}">{esc(v)}</a>' for k, v in SECTORS)
    crumbs = crumbs_html(c, page['sections'][1].get('crumbs'))
    title = {'current': 'Current Clients', 'past': 'Past Clients'}[status]
    body = (hero + crumbs + f'<section class="sec tone-paper clients" data-clients data-status="{status}" data-sector="{sector}" '
            f'data-base="{esc(c.link(BASE + "/clients"))}"><div class="wrap">'
            f'<div class="cl-filters"><div class="cl-row"><p class="tag">Status</p><div class="chips">{st_btn}</div></div>'
            f'<div class="cl-row"><p class="tag">Sectors</p><div class="chips chips-wrap">{sec_btn}</div></div></div>'
            f'<div class="cl-head"><h2 class="h-l" data-cl-title>{title}</h2><p class="count"><b data-count-out>0</b></p></div>'
            f'<ul class="logos" data-logos>{"".join(x[1] for x in items)}</ul>'
            f'<p class="cl-empty" hidden data-empty>—</p></div></section>')
    return shell(c, page, body, 'is-clients')


def list_items(page, kind):
    s = raw_soup(page)
    c = Ctx(page['path'])
    out = {'featured': None, 'items': []}
    def parse(el, featured=False):
        h3 = el.find('h3'); date = el.select_one('.date'); p = el.find('p')
        auth = el.select_one('.author')
        a = el.select_one('a[href]')
        img = el.find('img') if not featured else None
        href = a.get('href') if a else ''
        if href and kind == 'blog' and not href.startswith('http'):
            href = BASE + '/blog/' + href
        logo = auth.find('img') if auth else None
        return {'title': norm(h3.get_text()) if h3 else '', 'date': norm(date.get_text()) if date else '',
                'p': norm(p.get_text(' ')) if p else '', 'href': href,
                'img': urllib.parse.urljoin(BASE + '/', img.get('src')) if img else '', 'alt': norm(img.get('alt', '')) if img else '',
                'logo': urllib.parse.urljoin(BASE + '/', logo.get('src')) if logo else '', 'logo_alt': norm(logo.get('alt', '')) if logo else '',
                'author': norm(auth.get_text(' ')) if auth else '', 'btn': norm(a.get_text()) if a else ''}
    f = s.select_one('.latest-news')
    if f:
        d = parse(f, True)
        m = re.search(r'url\(([^)]+)\)', f.get('style', ''))
        d['bg'] = m.group(1).strip('\'" ') if m else ''
        h2 = f.find('h2'); sm = h2.find('small') if h2 else None
        d['eyebrow'] = norm(sm.get_text()) if sm else ''
        if sm: sm.extract()
        d['h2'] = norm(h2.get_text()) if h2 else ''
        mob = f.find('img', class_='img-fluid')
        d['mob'] = urllib.parse.urljoin(BASE + '/', mob.get('src')) if mob else ''
        out['featured'] = d
    for it in s.select('.news-grid .news-item'):
        out['items'].append(parse(it))
    return out


def page_list(page, kind):
    c = Ctx(page['path'])
    hero = hero_from(c, page['sections'][0])
    crumbs = crumbs_html(c, page['sections'][1].get('crumbs')) if len(page['sections']) > 1 else ''
    d = list_items(page, kind)
    f = d['featured']
    feat = ''
    if f:
        link = c.link(f['href']) if f['href'] else ''
        ext = ' target="_blank" rel="noopener"' if link.startswith('http') else ''
        feat = (f'<article class="feature"><div class="feature-media">{pic(c, f["bg"], "", "")}</div>'
                f'<div class="feature-txt"><h2 class="h-l"><span class="eyebrow">{esc(f["eyebrow"])}</span> <span class="ht">{esc(f["h2"])}</span></h2>'
                f'<p class="news-date">{esc(f["date"])}</p><h3 class="h-m">{esc(f["title"])}</h3><p class="txt">{esc(f["p"])}</p>'
                f'<p class="byline">{pic(c, f["logo"], f["logo_alt"], "byline-logo")}{esc(f["author"])}</p>'
                + (f'<a class="btn" href="{esc(link)}"{ext}>{esc(f["btn"])}{ARROW}</a>' if link else '')
                + (f'<span hidden>{pic(c, f["mob"], "", "")}</span>' if f.get('mob') else '') + '</div></article>')
    cards = []
    for i, it in enumerate(d['items']):
        link = c.link(it['href']) if it['href'] else ''
        ext = ' target="_blank" rel="noopener"' if link.startswith('http') else ''
        inner = (f'<span class="post-media">{pic(c, it["img"], it["alt"], "")}</span><span class="post-body">'
                 f'<span class="news-date">{esc(it["date"])}</span><span class="post-t">{esc(it["title"])}</span>'
                 f'<span class="txt">{esc(it["p"])}</span><span class="byline">{pic(c, it["logo"], it["logo_alt"], "byline-logo")}{esc(it["author"])}</span>'
                 + (f'<span class="btn">{esc(it["btn"])}{ARROW}</span>' if link and it['btn'] else '') + '</span>')
        if link:
            cards.append(f'<a class="post reveal" style="--i:{i % 6}" href="{esc(link)}"{ext}>{inner}</a>')
        else:
            cards.append(f'<article class="post reveal" style="--i:{i % 6}">{inner}</article>')
    sm = raw_soup(page).select_one('.see-more')
    more = f'<p hidden><a href="#">{esc(norm(sm.get_text()))}</a></p>' if sm else ''
    body = hero + crumbs + f'<section class="sec tone-paper listing"><div class="wrap">{feat}<div class="posts">{"".join(cards)}</div>{more}</div></section>'
    return shell(c, page, body, f'is-{kind}')


def page_generic(page):
    c = Ctx(page['path'])
    # stable anchors for What We Do (home links to /what-we-do/#digital-strategy etc.)
    if clean_path(page['path']) == '/what-we-do':
        for s in page['sections']:
            nb = []
            for b in s['blocks']:
                if b['t'] == 'h' and norm(re.sub('<[^>]+>', '', b['html'])) in WWD_ANCHORS:
                    b = dict(b); b['html'] = f'<span id="{WWD_ANCHORS[norm(re.sub("<[^>]+>", "", b["html"]))]}" class="anchor"></span>' + b['html']
                nb.append(b)
            s['blocks'] = nb
    body = generic_sections(c, page)
    kind = {'/contact-us': 'is-contact', '/careers': 'is-careers', '/about-us': 'is-about'}.get(clean_path(page['path']), 'is-page')
    return shell(c, page, body, kind)


def redirect_page(src, dst):
    c = Ctx(src)
    href = c.link(BASE + dst)
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Redirecting…</title>'
            f'<meta http-equiv="refresh" content="0; url={esc(href)}"><link rel="canonical" href="{esc(BASE + urllib.parse.quote(dst))}">'
            f'<meta name="robots" content="noindex"></head><body><p><a href="{esc(href)}">Continue</a></p>'
            f'<script>location.replace({json.dumps(href)}+location.hash)</script></body></html>')


def write(rel, content):
    d = os.path.join(DOCS, *[s for s in rel.split('/') if s])
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, 'index.html'), 'w', encoding='utf-8').write(content)


def main():
    built = []
    for page in P:
        path = clean_path(page['path'])
        t = page['type']
        if t == 'junk':
            continue
        if t == 'home': h = page_home(page)
        elif t == 'work': h = page_work(page)
        elif t == 'work-detail': h = page_work_detail(page)
        elif t == 'clients': h = page_clients(page, 'current', 'all')
        elif t == 'clients-filter':
            parts = path.split('/')
            h = page_clients(page, parts[2].replace('-clients', ''), parts[3] if len(parts) > 3 else 'all')
        elif t in ('news', 'blog'): h = page_list(page, t)
        else: h = page_generic(page)
        write(out_rel(path), h)
        built.append(path)
    # redirects for duplicate / broken-link URLs that the old site served
    for src, dst in REDIRECTS.items():
        if out_rel(src) and not os.path.exists(os.path.join(DOCS, *out_rel(src).split('/'), 'index.html')):
            write(out_rel(src), redirect_page(src, dst))
    # 404 router: original URLs whose characters can't exist on disk (e.g. "|") resolve here
    alias = {}
    for path in built:
        if out_rel(path) != path.strip('/'):
            alias[path] = out_rel(path)
    for src, dst in REDIRECTS.items():
        alias[src] = out_rel(dst)
    router = ('<script>(function(){var m=%s;var root=document.baseURI;var rp=new URL(root).pathname;'
              'var p=decodeURIComponent(location.pathname);if(p.indexOf(rp)===0)p="/"+p.slice(rp.length);p=p.replace(/\\/+$/,"")||"/";'
              'if(m[p]!==undefined){location.replace(root+m[p].split("/").map(encodeURIComponent).join("/")+(m[p]?"/":"")+location.hash);}})();</script>') % json.dumps(alias, ensure_ascii=False)
    notfound = shell(Ctx('/'), {'path': '/404', 'meta': {'title': 'Icon Creations'}},
                     '<section class="sec tone-ink nf"><div class="wrap"><p class="h-xl">404</p>'
                     f'<p class="lede"><a class="btn" href="./">Home{ARROW}</a></p></div></section>' + router)
    # 404.html is served for any depth, so resolve relative assets against the site root (GitHub project pages or a custom domain)
    base_js = '<script>document.write(\'<base href="\'+(location.hostname.endsWith("github.io")?"/"+location.pathname.split("/")[1]+"/":"/")+\'">\')</script>'
    notfound = notfound.replace('<head>', '<head>\n' + base_js, 1)
    open(os.path.join(DOCS, '404.html'), 'w', encoding='utf-8').write(notfound)
    json.dump({'built': built, 'redirects': REDIRECTS, 'aliases': alias}, open(os.path.join(AUD, 'build-map.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    # sitemap
    urls = ''.join(f'<url><loc>{esc(BASE + urllib.parse.quote(p) if p != "/" else BASE + "/")}</loc></url>' for p in built)
    open(os.path.join(DOCS, 'sitemap.xml'), 'w', encoding='utf-8').write(f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>')
    open(os.path.join(DOCS, 'robots.txt'), 'w').write('User-agent: *\nAllow: /\nSitemap: https://icon-creations.com/sitemap.xml\n')
    open(os.path.join(DOCS, '.nojekyll'), 'w').write('')
    print('built', len(built), 'redirects', len(REDIRECTS), 'aliases', len(alias))


if __name__ == '__main__':
    main()
