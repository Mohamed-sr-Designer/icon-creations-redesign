/* ICON Creations: interaction layer (vanilla, no dependencies) */
(() => {
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  document.documentElement.classList.remove('no-js');

  /* top bar: solid on scroll, hide on scroll down */
  const bar = $('[data-bar]');
  let lastY = 0;
  const onScroll = () => {
    const y = scrollY;
    bar.classList.toggle('is-solid', y > 40);
    bar.classList.toggle('is-hidden', y > 400 && y > lastY && !document.body.classList.contains('menu-open'));
    lastY = y;
  };
  addEventListener('scroll', onScroll, { passive: true }); onScroll();

  /* menu */
  const menuBtn = $('[data-menu]'), menu = $('#menu');
  const setMenu = (open) => {
    menuBtn.setAttribute('aria-expanded', open);
    $('.bar-menu-l', menuBtn).textContent = open ? 'Close' : 'Menu';
    document.body.classList.toggle('menu-open', open);
    if (open) { menu.hidden = false; requestAnimationFrame(() => menu.classList.add('is-open')); $('a', menu).focus({ preventScroll: true }); }
    else { menu.classList.remove('is-open'); setTimeout(() => { if (!menu.classList.contains('is-open')) menu.hidden = true; }, reduce ? 0 : 700); }
  };
  menuBtn.addEventListener('click', () => setMenu(menuBtn.getAttribute('aria-expanded') !== 'true'));
  addEventListener('keydown', (e) => { if (e.key === 'Escape' && document.body.classList.contains('menu-open')) { setMenu(false); menuBtn.focus(); } });

  /* reveal on scroll */
  if ('IntersectionObserver' in window && !reduce) {
    const io = new IntersectionObserver((es) => es.forEach((e) => { if (e.isIntersecting) { e.target.classList.add('is-in'); io.unobserve(e.target); } }), { rootMargin: '0px 0px -8% 0px' });
    $$('.reveal').forEach((el) => io.observe(el));
  } else $$('.reveal').forEach((el) => el.classList.add('is-in'));

  /* counters */
  if ('IntersectionObserver' in window && !reduce) {
    const co = new IntersectionObserver((es) => es.forEach((e) => {
      if (!e.isIntersecting) return; co.unobserve(e.target);
      const el = e.target, raw = el.dataset.count, target = parseFloat(raw.replace(/,/g, ''));
      if (isNaN(target)) return;
      const dec = (raw.split('.')[1] || '').length, t0 = performance.now(), dur = 1400;
      const tick = (t) => { const k = Math.min(1, (t - t0) / dur), v = target * (1 - Math.pow(1 - k, 3)); el.textContent = k < 1 ? v.toFixed(dec) : raw; if (k < 1) requestAnimationFrame(tick); };
      requestAnimationFrame(tick);
    }), { threshold: .6 });
    $$('.num[data-count]').forEach((el) => co.observe(el));
  }

  /* hero slider (home + work) */
  $$('[data-heroslider]').forEach((h) => {
    const slides = $$('[data-slide]', h), dots = $$('.hs-dot', h), pause = $('.hs-pause', h);
    if (slides.length < 2) { $('.hs-ctl', h) && ($('.hs-ctl', h).hidden = true); return; }
    let i = 0, timer, paused = reduce;
    const DUR = 6000; h.style.setProperty('--dur', DUR + 'ms');
    const go = (n) => {
      slides[i].classList.remove('is-on'); dots[i].classList.remove('is-on');
      i = (n + slides.length) % slides.length;
      slides[i].classList.add('is-on'); void dots[i].offsetWidth; dots[i].classList.add('is-on');
      schedule();
    };
    const schedule = () => { clearTimeout(timer); if (!paused) timer = setTimeout(() => go(i + 1), DUR); };
    dots.forEach((d, k) => d.addEventListener('click', () => go(k)));
    const setPause = (p) => { paused = p; h.classList.toggle('is-paused', p); pause.setAttribute('aria-pressed', p); pause.setAttribute('aria-label', p ? 'Play slideshow' : 'Pause slideshow'); schedule(); };
    pause.addEventListener('click', () => setPause(!paused));
    setPause(paused);
    let x0 = null;
    h.addEventListener('touchstart', (e) => { x0 = e.touches[0].clientX; }, { passive: true });
    h.addEventListener('touchend', (e) => { if (x0 === null) return; const dx = e.changedTouches[0].clientX - x0; if (Math.abs(dx) > 50) go(i + (dx < 0 ? 1 : -1)); x0 = null; });
    document.addEventListener('visibilitychange', () => { if (document.hidden) clearTimeout(timer); else schedule(); });
  });

  /* rails */
  $$('[data-rail]').forEach((r) => {
    const track = $('.rail-track', r), items = Array.from(track.children), count = $('.rail-count b', r);
    const [prev, next] = $$('.rail-btn', r);
    const step = () => (items[0] ? items[0].getBoundingClientRect().width + parseFloat(getComputedStyle(track).columnGap || 0) : track.clientWidth);
    const update = () => {
      const idx = Math.round(track.scrollLeft / step());
      if (count) count.textContent = String(Math.min(items.length, idx + 1)).padStart(2, '0');
      prev.disabled = track.scrollLeft < 4; next.disabled = track.scrollLeft + track.clientWidth >= track.scrollWidth - 4;
    };
    [prev, next].forEach((b) => b.addEventListener('click', () => track.scrollBy({ left: step() * +b.dataset.dir, behavior: reduce ? 'auto' : 'smooth' })));
    track.addEventListener('scroll', () => requestAnimationFrame(update), { passive: true });
    addEventListener('resize', update); update();
    if (items.length < 2) $('.rail-ctl', r).hidden = true;
  });

  /* home work tabs */
  $$('[role="tablist"]').forEach((tl) => {
    const scope = tl.closest('.sec'), tabs = $$('[role="tab"]', tl), panes = $$('[data-pane]', scope);
    const sel = (k) => { tabs.forEach((t, j) => t.setAttribute('aria-selected', j === k)); panes.forEach((p, j) => { p.hidden = j !== k; if (j === k) $$('.reveal', p).forEach((c) => c.classList.add('is-in')); }); };
    tabs.forEach((t, k) => {
      t.addEventListener('click', () => sel(k));
      t.addEventListener('keydown', (e) => { if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') { const n = (k + (e.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length; tabs[n].focus(); sel(n); } });
    });
  });

  /* work filter */
  const grid = $('[data-filter-grid]');
  if (grid) {
    const chips = $$('[data-filter]'), cards = $$('.card', grid), out = $('[data-count-out]');
    const apply = (f, push) => {
      let n = 0;
      cards.forEach((c) => { const show = f === 'All' || c.dataset.cats.split('|').includes(f); c.hidden = !show; if (show) { n++; c.classList.add('is-in'); } });
      chips.forEach((ch) => ch.setAttribute('aria-pressed', ch.dataset.filter === f));
      grid.classList.toggle('is-filtered', f !== 'All');
      out.textContent = n;
      if (push) history.replaceState(null, '', f === chips[0].dataset.filter ? location.pathname : '#' + encodeURIComponent(f));
    };
    chips.forEach((ch) => ch.addEventListener('click', () => apply(ch.dataset.filter, true)));
    const fromHash = decodeURIComponent(location.hash.slice(1));
    apply(chips.some((c) => c.dataset.filter === fromHash) ? fromHash : chips[0].dataset.filter, false);
  }

  /* clients filter (status x sector), keeps the original /clients/<status>-clients/<sector> URLs */
  const cl = $('[data-clients]');
  if (cl) {
    const logos = $$('.logo', cl), list = $('[data-logos]', cl), title = $('[data-cl-title]', cl), out = $('[data-count-out]', cl), empty = $('[data-empty]', cl);
    let st = cl.dataset.status, sec = cl.dataset.sector;
    const titles = { current: 'Current Clients', past: 'Past Clients' };
    const render = () => {
      let n = 0;
      const vis = logos.filter((l) => l.dataset.st.split(' ').includes(st) && (sec === 'all' || l.dataset.sec.split(' ').includes(sec)));
      vis.sort((a, b) => +a.dataset['o' + st[0].toUpperCase() + st.slice(1)] - +b.dataset['o' + st[0].toUpperCase() + st.slice(1)]);
      logos.forEach((l) => { l.hidden = true; });
      vis.forEach((l) => { l.hidden = false; list.appendChild(l); n++; });
      title.textContent = titles[st]; out.textContent = n; empty.hidden = n > 0;
      $$('[data-st]', cl).forEach((a) => { if (a.classList.contains('chip')) a.setAttribute('aria-pressed', a.dataset.st === st); });
      $$('.chip[data-sec]', cl).forEach((a) => a.setAttribute('aria-pressed', a.dataset.sec === sec));
      list.classList.remove('is-anim'); void list.offsetWidth; if (!reduce) list.classList.add('is-anim');
    };
    const hrefFor = (s, c) => { const base = cl.dataset.base.replace(/\/?$/, '/'); return base + s + '-clients/' + (c === 'all' ? '' : c + '/'); };
    $$('.chip', cl).forEach((a) => a.addEventListener('click', (e) => {
      e.preventDefault();
      if (a.dataset.st) st = a.dataset.st; if (a.dataset.sec) sec = a.dataset.sec;
      render(); history.pushState({ st, sec }, '', hrefFor(st, sec));
    }));
    addEventListener('popstate', (e) => { if (e.state) { st = e.state.st; sec = e.state.sec; render(); } });
    history.replaceState({ st, sec }, '');
    render();
  }

  /* lightbox for galleries */
  const lb = $('#lightbox');
  if (lb && lb.showModal) {
    let set = [], k = 0;
    const lbImg = $('img', lb);
    const show = (n) => { k = (n + set.length) % set.length; lbImg.src = set[k]; };
    document.addEventListener('click', (e) => {
      const b = e.target.closest('[data-lightbox]');
      if (!b) return;
      const g = b.closest('.gallery') || b.parentElement;
      set = $$('[data-lightbox]', g).map((x) => x.dataset.lightbox); show(set.indexOf(b.dataset.lightbox));
      lb.showModal();
    });
    $('.lb-prev', lb).addEventListener('click', () => show(k - 1));
    $('.lb-next', lb).addEventListener('click', () => show(k + 1));
    lb.addEventListener('keydown', (e) => { if (e.key === 'ArrowLeft') show(k - 1); if (e.key === 'ArrowRight') show(k + 1); });
    lb.addEventListener('click', (e) => { if (e.target === lb) lb.close(); });
  }

  /* dialogs (careers job details) */
  document.addEventListener('click', (e) => {
    const o = e.target.closest('[data-dialog]');
    if (o) { const d = document.getElementById(o.dataset.dialog); if (d && d.showModal) d.showModal(); return; }
    const c = e.target.closest('[data-close]');
    if (c) c.closest('dialog').close();
  });
  $$('dialog.modal').forEach((d) => d.addEventListener('click', (e) => { if (e.target === d) d.close(); }));

  /* YouTube facade: load the player only on click */
  document.addEventListener('click', (e) => {
    const p = e.target.closest('.vid-play');
    if (!p) return;
    const box = p.parentElement, src = box.dataset.src;
    const f = document.createElement('iframe');
    f.src = src + (src.includes('?') ? '&' : '?') + 'autoplay=1'; f.allow = 'autoplay; encrypted-media; picture-in-picture'; f.allowFullscreen = true; f.title = 'Video';
    box.replaceChildren(f);
  });

  /* forms: same field names + endpoints as the original site (contact-us/ajaxsubmit.php, ajaxsubmit.php) */
  $$('form[data-ajax]').forEach((f) => {
    f.addEventListener('submit', async (e) => {
      e.preventDefault();
      const err = $('.form-err', f), ok = $('.form-ok', f);
      let bad = 0;
      $$('input, textarea', f).forEach((i) => {
        if (i.type === 'hidden') return;
        const v = i.value.trim(), invalid = (i.required && !v) || (i.type === 'email' && v && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(v));
        i.closest('.fld') && i.closest('.fld').classList.toggle('invalid', invalid); if (invalid) bad++;
      });
      const note = $('.form-note', f);
      if (bad) { err.textContent = note ? note.textContent : 'Invalid e-mail address.'; err.hidden = false; return; }
      err.hidden = true; f.classList.add('is-sending');
      const data = new URLSearchParams(new FormData(f));
      if (data.has('email') && f.classList.contains('news-form')) { /* newsletter posts { email } */ }
      const utm = new URLSearchParams(location.search).get('utm_campaign'); if (utm && data.has('utm_campaign')) data.set('utm_campaign', utm);
      try {
        const r = await fetch(f.dataset.ajax, { method: 'POST', body: data, mode: 'cors' });
        const t = (await r.text()).trim();
        if (!r.ok) throw new Error(r.status);
        f.reset(); if (ok) ok.hidden = false; else { err.textContent = t || 'Thank you'; err.hidden = false; }
      } catch (x) {
        err.textContent = 'info@icon-creations.com'; err.hidden = false;
      } finally { f.classList.remove('is-sending'); }
    });
  });
})();
