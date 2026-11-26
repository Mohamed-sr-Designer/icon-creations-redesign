# ICON Creations: complete website redesign

A full UX/UI redesign of [icon-creations.com](https://icon-creations.com) that keeps **100% of the original content**: every text, image, video, project, client, article and URL. Only presentation, information architecture, navigation, interaction and responsive layout changed.

The site is static HTML/CSS/JS in [`docs/`](docs/) (ready for GitHub Pages or any static host). It is generated from a byte-exact crawl of the live site, so nothing was retyped or rewritten by hand.

## What's in the repo

| Path | Purpose |
|---|---|
| `docs/` | The redesigned website (190 pages + redirects, sitemap, robots, 404 router) |
| `docs/assets/site.css` | "Signal Grid" design system (tokens, type scale, components, motion) |
| `docs/assets/site.js` | Interaction layer, vanilla JS, no dependencies |
| `docs/uploads/`, `docs/images/` | All original media, mirrored at their original paths |
| `docs/_opt/` | WebP derivatives (max 1600px) served first for speed; originals stay as fallback |
| `tools/extract.py` | Phase 01 audit: parses every crawled page into a structured content model |
| `tools/media.py` | Mirrors every referenced image/video |
| `tools/optimize.py` | Builds WebP derivatives + image dimensions (prevents layout shift) |
| `tools/build.py` | Renders the new site from the content model |
| `tools/validate.py` | Mandatory validation: original vs redesigned, page by page |
| `_audit/` | Crawl (raw bytes), content inventory, media inventory, build map, validation report |

Rebuild everything:

```
python tools/extract.py && python tools/media.py && python tools/optimize.py && python tools/build.py && python tools/validate.py
```

Preview locally: `python -m http.server 8765 --directory docs` and open http://localhost:8765

## Phase 01: audit (inventory)

Crawled **282 URLs** on the live site:

- **190 real pages**: home, About Us, What We Do, 7 service pages, Investor Relations, Work index, **122 case studies**, Clients + **34 status/sector filter views**, Sustainability, News, Blog, **6 blog articles**, Careers (with 4 full job descriptions), Contact Us.
- **92 duplicate/broken URLs** the old site served because of broken relative links (for example `/12/CIB-...` and `/clients/current-clients/<blog-slug>`). These now redirect to the page they were meant to reach.
- **1,804 media files** mirrored (397 MB). 46 tablet/mobile banner variants already return 404 on the live site, so those fall back to the desktop banner. Two `<img>` tags on the live site have an empty filename (`/uploads/blog/banner/`, `/uploads/work/gallery/`); they were broken there too.

Full inventory: `_audit/content.json`, `_audit/media.json`, `_audit/build-map.json`.

## Phase 02: UX and architecture

Problems found on the old site, and what changed:

| Issue on the old site | Redesign |
|---|---|
| 10 nav items plus 7 duplicated icon rows in the header | Minimal bar (logo, Contact Us, Menu) + full-screen numbered menu with contact details and socials |
| Blog "See More" links were relative and led to a Clients page | Links resolve to the right article; the old broken URLs redirect |
| Clients: 34 separate server-rendered filter pages, one carousel of 6 logos at a time | One logo wall with Status × Sector filters; every original filter URL still works and stays in the address bar |
| Work: hidden tab filters, no counts | Sticky filter chips with live counts, numbered project index, shareable `#filter` |
| Case studies: popup duplicates of every gallery image, swiper with "Next/Previous" text | Masonry gallery + keyboard lightbox, scroll-snap rails with counters, prev/next project navigation |
| Careers: job details hidden in jQuery popups | Native `<dialog>` modals (focusable, Esc to close) |
| Home "What We Do" cards linked to anchors that didn't exist | Stable anchors added on What We Do |
| Mixed encodings broke apostrophes ("we�ve") | Decoded correctly, text unchanged |

Sitemap (unchanged URLs): `/`, `/about-us`, `/what-we-do` → 7 service pages + `/investor-relations`, `/work` → `/work/<category>/<id>/<slug>`, `/clients` → `/clients/<current|past>-clients/<sector>`, `/sustainability`, `/news`, `/blog` → `/blog/<id>/<slug>`, `/careers`, `/contact-us`.

## Phase 03: creative direction, "Signal Grid"

- **Concept**: the dot matrix in the ICON logo becomes the interaction language (menu button, hover veils on projects, slide progress, footer mark).
- **Color**: ink `#0B0C0E` and warm paper `#F2F0EB` alternate like editorial spreads; navy `#174170` and signal cyan `#28ABE1` come from the logo and are used sparingly.
- **Type**: Archivo (variable width, wide cuts for display), Instrument Serif italic for the original two-part headings ("*Hello, We Are* Icon Creations", "*Our* Services"), IBM Plex Sans Arabic for Arabic.
- **Art direction**: banners are composed artwork, so they're always shown uncropped; headlines sit in the empty zone the original art left for them (left on desktop, sky on mobile).
- **Motion**: cross-document view transitions, scroll reveals, Ken Burns on banners, counter roll-ups. Everything is disabled under `prefers-reduced-motion`.

## Phase 04 and 05: UI and build

Every page type has a mobile-first layout tested at 375 px, tablet and desktop. Accessibility: skip link, semantic landmarks, breadcrumbs, `aria-pressed` filters, keyboard tabs, labelled controls, focus rings, pause control on the auto slideshow. Performance: WebP with original fallback, width/height on every image, lazy loading, YouTube click-to-load facades, no frameworks.

## Validation (see `_audit/VALIDATION.md`)

- Pages compared: **190**
- Text fragments checked: **9,461**, missing: **0**
- Images checked: **2,566**, missing: **0** (excluding files already broken on the live site, listed above)
- Embedded videos checked: **99**, missing: **0**
- Internal links/assets in `docs/`: broken: **0**
- No horizontal overflow at 375 px on any page template

## Known limitations

- **Forms** post to the original endpoints (`/contact-us/ajaxsubmit.php`, `/ajaxsubmit.php`) with the original field names. They work once deployed on icon-creations.com; from another domain (GitHub Pages preview) the browser blocks the request (CORS).
- **URLs containing `|`** (one case study, Kalem Masr) can't exist as folder names, so the page is stored with `-`; `404.html` maps the original URL to it.
- Social icon images in the old header/footer were replaced by text links (same destinations). Tracking tags (GTM, Messenger chat) were not carried over; add them back at deployment.
- Facebook video embeds depend on Facebook's player and may need the visitor to be logged in.
