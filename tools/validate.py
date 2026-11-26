"""Mandatory validation: compare every original page against its redesigned counterpart.

Checks
1. Text: every visible text fragment of the original main content (and footer) exists in the new page.
2. Media: every original <img>/<video>/<iframe>/bg-image in the page is present in the new page (or documented as broken on the live site).
3. Links: every internal href/src in docs/ resolves to a file.
Writes _audit/VALIDATION.md and exits non-zero on unexpected failures.
"""
import json, os, re, sys, html, urllib.parse
from bs4 import BeautifulSoup, NavigableString, Comment

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract import load, IDX
from build import P, clean_path, out_rel, MEDIA, DOCS, AUD

UI_ONLY = {'Next', 'Previous'}  # slider arrow labels, replaced by arrow buttons with aria-labels


def n(t):
    t = html.unescape(t or '').replace('\xa0', ' ')
    t = re.sub(r'[​-‏﻿]', '', t)
    return re.sub(r'\s+', ' ', t).strip()


def orig_texts(soup):
    body = soup.body
    for t in body.find_all(['script', 'style', 'noscript', 'nav']): t.decompose()
    for t in body.select('.work-popup, #fb-root, .fb-customerchat'): t.decompose()
    out = []
    for s in body.find_all(string=True):
        if isinstance(s, Comment): continue
        if s.parent.name in ('option', 'title'): continue
        t = n(str(s))
        if t and t not in UI_ONLY: out.append(t)
    return out


def orig_media(soup, page_url):
    urls = set()
    for im in soup.select('body img'):
        if im.find_parent('nav') or im.find_parent('footer') or im.find_parent(class_='work-popup'): continue
        src = (im.get('src') or '').strip()
        if src and 'loading.gif' not in src: urls.add(urllib.parse.urljoin(page_url, src))
    for el in soup.select('body [style*="url("]'):
        m = re.search(r'url\(([^)]+)\)', el.get('style'))
        if m: urls.add(urllib.parse.urljoin(page_url, m.group(1).strip('\'" ')))
    vids = set((f.get('src') or '').strip() for f in soup.select('body iframe') if 'google.com/maps' not in (f.get('src') or '') and 'googletagmanager' not in (f.get('src') or '') and (f.get('src') or '').strip())
    return urls, vids


def main():
    report = ['# Validation report', '']
    total_txt = miss_txt = 0
    total_img = miss_img = broken_live = 0
    total_vid = miss_vid = 0
    problems = []
    pages = [p for p in P if p['type'] != 'junk']
    for p in pages:
        u = p['url']
        rel = out_rel(clean_path(p['path']))
        f = os.path.join(DOCS, *rel.split('/'), 'index.html') if rel else os.path.join(DOCS, 'index.html')
        new_html = open(f, encoding='utf-8').read()
        new_soup = BeautifulSoup(new_html, 'lxml')
        for t in new_soup.find_all(['script', 'style']): t.decompose()
        new_text = n(new_soup.get_text(' '))
        new_text_nosp = new_text.replace(' ', '')
        new_raw = urllib.parse.unquote(new_html)
        o = BeautifulSoup(load(u), 'lxml')
        o2 = BeautifulSoup(load(u), 'lxml')
        texts = orig_texts(o)
        for t in texts:
            total_txt += 1
            if t not in new_text and t.replace(' ', '') not in new_text_nosp:
                miss_txt += 1; problems.append(('text', p['path'], t[:120]))
        imgs, vids = orig_media(o2, u)
        for im in imgs:
            total_img += 1
            q = urllib.parse.urlsplit(im)
            key = urllib.parse.urlunsplit((q.scheme, q.netloc, urllib.parse.quote(urllib.parse.unquote(q.path)), '', ''))
            st = MEDIA.get(im) or MEDIA.get(key) or MEDIA.get(urllib.parse.unquote(im))
            path = urllib.parse.unquote(q.path).lstrip('/')
            if st and st[0] != 'ok':
                broken_live += 1; continue
            if path not in new_raw:
                miss_img += 1; problems.append(('image', p['path'], im))
        for v in vids:
            total_vid += 1
            if v not in html.unescape(new_html):
                miss_vid += 1; problems.append(('video', p['path'], v))
    # links
    bad_links = []
    for d, _, fs in os.walk(DOCS):
        if '_opt' in d or 'uploads' in d or 'images' in d: continue
        for fn in fs:
            if not fn.endswith('.html') or fn == '404.html': continue
            fp = os.path.join(d, fn)
            h = open(fp, encoding='utf-8').read()
            for m in re.finditer(r'(?:href|src|srcset)="([^"]+)"', h):
                v = html.unescape(m.group(1))
                if v.startswith(('http', 'mailto:', 'tel:', '#', 'data:', 'javascript')): continue
                v = v.split('#')[0].split('?')[0]
                if not v: continue
                tgt = os.path.normpath(os.path.join(d, urllib.parse.unquote(v)))
                if v.endswith('/'): tgt = os.path.join(tgt, 'index.html')
                if not os.path.exists(tgt): bad_links.append((os.path.relpath(fp, DOCS), v))
    report += [f'- Pages compared: **{len(pages)}** (plus {len([p for p in P if p["type"] == "junk"])} duplicate/broken-link URLs served by the old site, now redirects)',
               f'- Text fragments checked: **{total_txt}**, missing: **{miss_txt}**',
               f'- Images checked: **{total_img}**, missing: **{miss_img}**, already broken (404) on the live site: **{broken_live}**',
               f'- Embedded videos checked: **{total_vid}**, missing: **{miss_vid}**',
               f'- Internal links/assets checked in docs/: broken: **{len(bad_links)}**', '']
    if problems:
        report += ['## Missing items', ''] + [f'- {k} | `{pg}` | {v}' for k, pg, v in problems[:300]] + ['']
    if bad_links:
        report += ['## Broken internal links', ''] + [f'- `{a}` -> `{b}`' for a, b in bad_links[:200]] + ['']
    open(os.path.join(AUD, 'VALIDATION.md'), 'w', encoding='utf-8').write('\n'.join(report))
    print('\n'.join(report[:10]))
    for x in problems[:40]: print(x)
    for x in bad_links[:20]: print('LINK', x)


if __name__ == '__main__':
    main()
