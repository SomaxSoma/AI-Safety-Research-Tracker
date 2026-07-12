/* AI Safety Research Tracker — page logic. */
(function () {
  'use strict';

  const state = {
    view: 'overview',
    expanded: false,
    p: 1,
    sdYear: '2026',
    sdScale: 'fixed',
    sdFace: 'all',
    confFace: 'pooled',
    orgFace: 'orgs',
  };

  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  const fmt = (n) => n.toLocaleString('en-US');

  const SD_FIXED_MAX = Math.max(...SD_RAW.map(([, , rows]) => Math.max(...rows.map((r) => r[1]))));

  /* ---------- number count-up ---------- */
  let raf = null, rafFallback = null;
  function animate(dur) {
    const t0 = performance.now();
    cancelAnimationFrame(raf);
    clearTimeout(rafFallback);
    const step = () => {
      const e = Math.min(1, (performance.now() - t0) / dur);
      state.p = 1 - Math.pow(1 - e, 3);
      paintNumbers();
      if (e < 1) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    // rAF is throttled in hidden/background tabs — make sure final values still land
    rafFallback = setTimeout(() => { state.p = 1; paintNumbers(); }, dur + 100);
  }
  function fmtBig(b, p) {
    const dec = b.dec || 0;
    const v = b.num * p;
    const num = dec > 0 ? v.toFixed(dec) : fmt(Math.round(v));
    return (b.pre || '') + num + (b.suf || '');
  }
  function paintNumbers() {
    $('hero-num').textContent = fmtBig({ num: 4.2, dec: 1, suf: '%' }, state.p);
    const el = document.querySelector('.pl-big');
    if (el) el.textContent = fmtBig(VIEWS[state.view].big, state.p);
  }

  /* ---------- tooltip ---------- */
  function ttInit() {
    const tt = $('tt');
    let visible = false;
    const move = (e) => {
      if (!visible) return;
      const pad = 14;
      let x = e.clientX + pad, y = e.clientY + pad + 2;
      const r = tt.getBoundingClientRect();
      if (x + r.width > window.innerWidth - 8) x = e.clientX - r.width - pad;
      if (y + r.height > window.innerHeight - 8) y = e.clientY - r.height - pad;
      tt.style.left = x + 'px';
      tt.style.top = y + 'px';
    };
    document.addEventListener('mouseover', (e) => {
      const el = e.target.closest ? e.target.closest('[data-tip]') : null;
      if (el) {
        tt.innerHTML = el.getAttribute('data-tip');
        visible = true;
        tt.classList.add('show');
        move(e);
      } else if (visible && !e.target.closest('#tt')) {
        visible = false;
        tt.classList.remove('show');
      }
    });
    document.addEventListener('mousemove', move);
  }

  /* ---------- hero ---------- */
  function renderHero() {
    const max = Math.max(...BY_YEAR.map((e) => e[1]));
    $('hero-bars').innerHTML = BY_YEAR.map(([year, share], i) => {
      const h = Math.max(3, (share / max) * 66).toFixed(0);
      const fill = share === max ? '#f2f2f2' : `rgba(255,255,255,${(0.3 + (share / max) * 0.5).toFixed(3)})`;
      return `<div class="hrow" data-tip="<span class='tt-em'>${year}</span> · ${share.toFixed(1)}% safety share">
        <div class="hero-bar-pct">${share.toFixed(1)}%</div>
        <div class="hero-bar-fill" style="height:${h}px;background:${fill};animation-delay:${i * 55}ms"></div>
      </div>`;
    }).join('');
    $('hero-bar-labels').innerHTML = BY_YEAR.map(([year]) => `<div>${year}</div>`).join('');
  }

  /* ---------- tabs ---------- */
  function renderTabs() {
    const focusWasInTabs = document.activeElement && document.activeElement.classList && document.activeElement.classList.contains('tab');
    $('tabs').innerHTML = VIEW_ORDER.map((k) =>
      `<div class="tab${k === state.view ? ' active' : ''}" data-view="${k}" role="tab" tabindex="0" aria-selected="${k === state.view}">${VIEWS[k].label}</div>`
    ).join('');
    $('tabs').querySelectorAll('.tab').forEach((el) => {
      el.addEventListener('click', () => requestView(el.dataset.view));
      el.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); requestView(el.dataset.view); return; }
        if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return;
        e.preventDefault();
        const i = VIEW_ORDER.indexOf(el.dataset.view);
        const j = e.key === 'ArrowLeft' ? (i + VIEW_ORDER.length - 1) % VIEW_ORDER.length : (i + 1) % VIEW_ORDER.length;
        requestView(VIEW_ORDER[j]);
      });
    });
    if (focusWasInTabs) {
      const active = $('tabs').querySelector('.tab.active');
      if (active) active.focus();
    }
  }
  /* deep-linkable views: tab activation goes through the URL hash */
  function requestView(key) {
    if (key === state.view) return;
    if (location.hash.slice(1) !== key) location.hash = key;
    else setView(key);
  }
  function setView(key) {
    if (key === state.view || !VIEWS[key]) return;
    state.view = key;
    state.expanded = false;
    state.sdFace = 'all';
    state.confFace = 'pooled';
    state.orgFace = 'orgs';
    renderTabs();
    renderPanel();
    renderDisclosure();
    animate(700);
  }
  window.addEventListener('hashchange', () => {
    const key = location.hash.slice(1);
    if (VIEWS[key]) setView(key);
  });

  /* ---------- chart builders ---------- */
  /* bar tooltip body: count plus a definition — per-entry override, else rubric glossary */
  function barTip(label, valueText, def) {
    def = def || GLOSSARY[label] || GLOSSARY[label.replace(/^[A-G] · /, '')];
    return `<span class='tt-em'>${esc(label)}</span> — ${valueText}` +
      (def ? `<br><span class='tt-dim'>${esc(def)}</span>` : '');
  }

  function mkHbars(entries, labelWidth) {
    const max = Math.max(...entries.map((e) => e[1]));
    const n = entries.length;
    return `<div class="hgrp hbars">` + entries.map(([label, value, def], i) => {
      const pct = ((value / max) * 100).toFixed(2);
      const fill = `rgba(255,255,255,${(0.92 - (i / Math.max(n - 1, 1)) * 0.6).toFixed(3)})`;
      return `<div class="hrow hbar" data-tip="${barTip(label, fmt(value) + ' papers', def)}">
        <div class="hbar-label"${labelWidth ? ` style="width:${labelWidth}px"` : ''}>${esc(label)}</div>
        <div class="hbar-track"><div class="hbar-fill" style="width:${pct}%;background:${fill};animation-delay:${i * 40}ms"></div></div>
        <div class="hbar-value">${fmt(value)}</div>
      </div>`;
    }).join('') + `</div>`;
  }

  /* WHO PUBLISHES: verified safety-org bars, by-legal-type face, and by-year trend face */
  function mkOrgs() {
    const v = VIEWS.orgs;
    if (state.orgFace === 'byyear') return mkOrgYears();
    const body = state.orgFace === 'types' ? mkHbars(ORG_TYPES_DIST) : mkHbars(ORGS_TOP);
    const note = state.orgFace === 'types'
      ? 'Papers per legal structure of the primary org (OpenAI counts as corporate before its 2026 PBC conversion, PBC after). Same 325-paper base and caveats as the org list.'
      : v.note;
    return `<div>${body}<div class="chart-note">${note}</div></div>`;
  }

  /* org-backed share of safety papers per year (data/org_verified.csv) */
  function mkOrgYears() {
    const shares = ORG_BY_YEAR.map(([, b, n]) => (n ? (b / n) * 100 : 0));
    const max = Math.max(...shares);
    const bars = ORG_BY_YEAR.map(([year, b, n], i) => {
      const share = shares[i];
      const h = Math.max(3, (share / max) * 196).toFixed(0);
      const fill = share === max ? '#f2f2f2' : `rgba(255,255,255,${(0.35 + (share / max) * 0.4).toFixed(3)})`;
      return `<div class="hrow vbar" data-tip="<span class='tt-em'>${year}</span> — ${share.toFixed(1)}% org-backed <span class='tt-dim'>(${b} of ${fmt(n)} checked)</span>">
        <div class="vbar-value" style="animation-delay:${i * 55}ms">${share.toFixed(0)}%</div>
        <div class="vbar-fill" style="height:${h}px;background:${fill};animation-delay:${i * 55}ms"></div>
      </div>`;
    }).join('');
    const labels = ORG_BY_YEAR.map(([year]) => `<div>${year}</div>`).join('');
    return `<div><div class="hgrp vbars">${bars}</div><div class="vbar-labels">${labels}</div>
      <div class="chart-note">Share of each year's checked safety papers with a confirmed primary safety-org. Early bars are tiny samples (2019: n=3) — the meaningful trend starts 2023: dedicated orgs' relative footprint shrinks as safety research mainstreams. Papers checked = full text retrievable; ICML 2026 excluded (no PDFs yet).</div></div>`;
  }

  /* subdomain composition over time: each line = share of that year's safety papers */
  function mkTrends() {
    const W = 640, CW = 552, H = 230, pt = 14, pb = 22;
    const years = SD_RAW.map((r) => r[0]);
    const totals = SD_RAW.map((r) => r[1]);
    const names = [...new Set(SD_RAW.flatMap(([, , rows]) => rows.map((r) => r[0])))];
    const series = names.map((name) => ({
      name,
      vals: SD_RAW.map(([, n, rows]) => {
        const f = rows.find((r) => r[0] === name);
        return f ? (f[1] / n) * 100 : 0;
      }),
    }));
    const max = Math.max(...series.flatMap((s) => s.vals)) * 1.08;
    const X = (i) => (i / (years.length - 1)) * CW;
    const Y = (v) => pt + (1 - v / max) * (H - pt - pb);
    const top = series.slice().sort((a, b) => b.vals[b.vals.length - 1] - a.vals[a.vals.length - 1]).slice(0, 6).map((s) => s.name);
    const shade = {};
    top.forEach((n, i) => { shade[n] = i === 0 ? '#f0f0f0' : `rgba(255,255,255,${(0.85 - i * 0.12).toFixed(2)})`; });
    const grid = [0, 0.25, 0.5, 0.75, 1].map((f) => {
      const y = pt + f * (H - pt - pb);
      return `<line x1="0" x2="${CW}" y1="${y.toFixed(1)}" y2="${y.toFixed(1)}" stroke="rgba(255,255,255,.07)" stroke-width="1"></line>
        <text x="-6" y="${(y + 3).toFixed(1)}" text-anchor="end" fill="#5a5a5a" font-family="IBM Plex Mono" font-size="9">${(max - f * max).toFixed(0)}%</text>`;
    }).join('');
    const lines = series.map((s) => {
      const p = s.vals.map((v, i) => (i ? 'L' : 'M') + X(i).toFixed(1) + ' ' + Y(v).toFixed(1)).join(' ');
      const isTop = top.includes(s.name);
      return `<path d="${p}" fill="none" stroke="${isTop ? shade[s.name] : 'rgba(255,255,255,.13)'}" stroke-width="${s.name === top[0] ? 1.8 : isTop ? 1.4 : 1}" stroke-linejoin="round"></path>`;
    }).join('');
    const hits = series.flatMap((s) => s.vals.map((v, i) => {
      const cnt = (SD_RAW[i][2].find((r) => r[0] === s.name) || [0, 0])[1];
      return `<circle class="hrow" cx="${X(i).toFixed(1)}" cy="${Y(v).toFixed(1)}" r="5.5" fill="transparent" data-tip="<span class='tt-em'>${esc(s.name)}</span> · ${years[i]} — ${v.toFixed(1)}% of that year's safety papers <span class='tt-dim'>(${cnt} of ${totals[i]})</span>"></circle>`;
    })).join('');
    const labels = top.map((n) => {
      const s = series.find((x) => x.name === n);
      return { n, y: Y(s.vals[s.vals.length - 1]) };
    }).sort((a, b) => a.y - b.y);
    for (let i = 1; i < labels.length; i++) if (labels[i].y - labels[i - 1].y < 11) labels[i].y = labels[i - 1].y + 11;
    const labelEls = labels.map((l) =>
      `<text x="${CW + 8}" y="${(l.y + 3).toFixed(1)}" fill="${shade[l.n]}" font-family="IBM Plex Mono" font-size="8.5" letter-spacing=".5">${esc(l.n.toUpperCase())}</text>`).join('');
    const xlabels = years.map((yr, i) =>
      `<text x="${X(i).toFixed(1)}" y="248" text-anchor="middle" fill="#5a5a5a" font-family="IBM Plex Mono" font-size="9">${yr}</text>`).join('');
    return `<svg class="line-svg" viewBox="-30 0 ${W + 30} 250">
      ${grid}
      <text transform="rotate(-90)" x="-208" y="-20" fill="#5a5a5a" font-family="IBM Plex Mono" font-size="9" letter-spacing="1.5">SHARE OF SAFETY PAPERS (%)</text>
      ${lines}${hits}${labelEls}${xlabels}
    </svg>
    <div class="line-caption">Each line: a subdomain's share of that year's safety papers — lines sum to 100% within a year, all venues pooled. The six largest 2026 subdomains are emphasized and labeled; hover any point for exact counts. Early years are tiny samples (2019: n=9) — read trends from 2023 on. Adversarial Robustness fell from 37% (2022) to 11%; Safeguards and Monitoring rose from zero.</div>`;
  }

  function mkVbars(entries, suf, note) {
    const max = Math.max(...entries.map((e) => e[1]));
    const bars = entries.map(([label, value], i) => {
      const h = Math.max(3, (value / max) * 196).toFixed(0);
      const fill = value === max ? '#f2f2f2' : `rgba(255,255,255,${(0.35 + (value / max) * 0.4).toFixed(3)})`;
      return `<div class="hrow vbar" data-tip="<span class='tt-em'>${esc(label)}</span> — ${fmt(value)}${suf}">
        <div class="vbar-value" style="animation-delay:${i * 55}ms">${fmt(value)}${suf}</div>
        <div class="vbar-fill" style="height:${h}px;background:${fill};animation-delay:${i * 55}ms"></div>
      </div>`;
    }).join('');
    const labels = entries.map(([label]) => `<div>${esc(label)}</div>`).join('');
    return `<div><div class="hgrp vbars">${bars}</div><div class="vbar-labels">${labels}</div>` +
      (note ? `<div class="chart-note">${note}</div>` : '') + `</div>`;
  }

  /* grouped per-venue bars: one group of 3 thin bars per year */
  function mkVenues() {
    const max = Math.max(...VENUE_SHARES.venues.flatMap((v) => v.rows.filter(Boolean).map((r) => r[0])));
    const groups = VENUE_SHARES.years.map((year, yi) => {
      const bars = VENUE_SHARES.venues.map((v, vi) => {
        const row = v.rows[yi];
        if (!row) return `<div class="vbar-thin" data-tip="<span class='tt-em'>${v.key} ${year}</span> — <span class='tt-dim'>not yet held</span>" style="height:2px;background:rgba(255,255,255,.08)"></div>`;
        const [share, safety, total] = row;
        const h = Math.max(2, (share / max) * 196).toFixed(0);
        return `<div class="vbar-thin" data-tip="<span class='tt-em'>${v.key} ${year}</span> — ${share.toFixed(1)}% <span class='tt-dim'>(${fmt(safety)} / ${fmt(total)})</span>" style="height:${h}px;background:${v.fill};animation-delay:${(yi * 3 + vi) * 22}ms"></div>`;
      }).join('');
      return `<div class="hrow vgroup">${bars}</div>`;
    }).join('');
    const labels = VENUE_SHARES.years.map((y) => `<div>${y}</div>`).join('');
    const legend = VENUE_SHARES.venues.map((v) =>
      `<span><span class="venue-swatch" style="background:${v.fill}"></span>${v.key}</span>`).join('');
    return `<div><div class="hgrp vbars">${groups}</div><div class="vbar-labels">${labels}</div>
      <div class="venue-legend">${legend}</div>
      <div class="chart-note">Safety share per venue and year — hover any bar for exact counts. NeurIPS 2026 not yet held. Highest single conference: ICML 2026 at 8.9%.</div></div>`;
  }

  function mkLine() {
    const W = 640, H = 230, pt = 14, pb = 22;
    const roll = ARXIV.roll, frac = ARXIV.frac, vol = ARXIV.vol, months = ARXIV.months;
    const n = roll.length;
    const max = Math.max(...roll, ...frac) * 1.08;
    const X = (i) => (i / (n - 1)) * W;
    const Y = (v) => pt + (1 - v / max) * (H - pt - pb);
    const mn = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const dlbl = (i) => {
      const [y, m] = months[i].split('-');
      return mn[parseInt(m, 10) - 1] + ' ' + y;
    };

    const linePath = roll.map((v, i) => (i ? 'L' : 'M') + X(i).toFixed(1) + ' ' + Y(v).toFixed(1)).join(' ');
    const lineArea = linePath + ` L ${W} ${H - pb} L 0 ${H - pb} Z`;
    const grid = [0, 0.25, 0.5, 0.75, 1].map((f) => {
      const y = pt + f * (H - pt - pb);
      return { y: y.toFixed(1), ty: (y - 4).toFixed(1), label: (max - f * max).toFixed(1) + '%' };
    });
    const vmax = Math.max(...vol);
    const volArea = vol.map((v, i) => (i ? 'L' : 'M') + X(i).toFixed(1) + ' ' + (H - pb - (v / vmax) * 44).toFixed(1)).join(' ') + ` L ${W} ${H - pb} L 0 ${H - pb} Z`;
    const xlabels = months.map((ym, i) => ({ ym, i })).filter(({ ym }) => ym.endsWith('-01'))
      .map(({ ym, i }) => `<text x="${X(i).toFixed(1)}" y="248" text-anchor="middle" fill="#5a5a5a" font-family="IBM Plex Mono" font-size="9">${ym.slice(0, 4)}</text>`).join('');
    const scatter = frac.map((v, i) =>
      `<circle cx="${X(i).toFixed(1)}" cy="${Y(v).toFixed(1)}" r="1.8" fill="rgba(255,255,255,.32)"></circle>`).join('');
    const peakI = vol.indexOf(vmax);

    return `<svg class="line-svg" id="line-svg" viewBox="0 0 640 250">
      ${grid.map((g) => `<line x1="0" x2="640" y1="${g.y}" y2="${g.y}" stroke="rgba(255,255,255,.07)" stroke-width="1"></line>
        <text x="640" y="${g.ty}" text-anchor="end" fill="#5a5a5a" font-family="IBM Plex Mono" font-size="9">${g.label}</text>`).join('')}
      <text transform="rotate(-90)" x="-208" y="-14" fill="#5a5a5a" font-family="IBM Plex Mono" font-size="9" letter-spacing="1.5">SHARE OF PAPERS (%)</text>
      <path d="${volArea}" fill="rgba(255,255,255,.06)"></path>
      ${scatter}
      <path d="${lineArea}" fill="rgba(255,255,255,.05)"></path>
      <path d="${linePath}" fill="none" stroke="#f0f0f0" stroke-width="1.6" stroke-linejoin="round" stroke-linecap="round"></path>
      <circle cx="${X(n - 1).toFixed(1)}" cy="${Y(roll[n - 1]).toFixed(1)}" r="3.4" fill="#060606" stroke="#fff" stroke-width="1.6"></circle>
      <g id="xh" style="display:none">
        <line class="xh-line" y1="${pt}" y2="${H - pb}" x1="0" x2="0"></line>
        <circle class="xh-dot" r="3.2" cx="0" cy="0"></circle>
      </g>
      ${xlabels}
      <text x="320" y="262" text-anchor="middle" fill="#5a5a5a" font-family="IBM Plex Mono" font-size="9" letter-spacing="1.5">SUBMISSION MONTH</text>
    </svg>
    <div class="line-caption">Dots: monthly share · line: rolling mean · shaded base: papers/month volume (peak ${fmt(vmax)}, ${dlbl(peakI)}). Hover the chart for exact values. arXiv AI papers: cs.LG · cs.AI · cs.CL · stat.ML, Jan 2019 – Jun 2026.</div>`;
  }

  /* crosshair readout over the arXiv chart: nearest month → rolling / monthly / volume */
  function attachLineHover() {
    const svg = $('line-svg');
    if (!svg) return;
    const W = 640, H = 230, pt = 14, pb = 22;
    const { roll, frac, vol, months } = ARXIV;
    const n = roll.length;
    const max = Math.max(...roll, ...frac) * 1.08;
    const X = (i) => (i / (n - 1)) * W;
    const Y = (v) => pt + (1 - v / max) * (H - pt - pb);
    const mn = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const xh = svg.querySelector('#xh');
    const xhLine = xh.querySelector('line');
    const xhDot = xh.querySelector('circle');
    const tt = $('tt');
    svg.addEventListener('mousemove', (e) => {
      const r = svg.getBoundingClientRect();
      const i = Math.max(0, Math.min(n - 1, Math.round(((e.clientX - r.left) / r.width) * (n - 1))));
      const x = X(i).toFixed(1);
      xh.style.display = '';
      xhLine.setAttribute('x1', x);
      xhLine.setAttribute('x2', x);
      xhDot.setAttribute('cx', x);
      xhDot.setAttribute('cy', Y(roll[i]).toFixed(1));
      const [yy, mm] = months[i].split('-');
      tt.innerHTML = `<span class="tt-em">${mn[parseInt(mm, 10) - 1]} ${yy}</span><br>` +
        `${roll[i].toFixed(1)}% rolling · ${frac[i].toFixed(1)}% monthly<br>` +
        `<span class="tt-dim">${fmt(vol[i])} papers/mo</span>`;
      tt.classList.add('show');
      const pad = 14;
      let tx = e.clientX + pad, ty = e.clientY + pad + 2;
      const tr = tt.getBoundingClientRect();
      if (tx + tr.width > window.innerWidth - 8) tx = e.clientX - tr.width - pad;
      if (ty + tr.height > window.innerHeight - 8) ty = e.clientY - tr.height - pad;
      tt.style.left = tx + 'px';
      tt.style.top = ty + 'px';
    });
    svg.addEventListener('mouseleave', () => {
      xh.style.display = 'none';
      tt.classList.remove('show');
    });
  }

  function mkDrill() {
    const yearRows = SD_RAW.map(([year, cnt]) =>
      `<div class="drill-year${year === state.sdYear ? ' active' : ''}" data-year="${year}">
        <span class="drill-year-y">${year}</span><span class="drill-year-n">n=${fmt(cnt)}</span>
      </div>`).join('');
    const sel = SD_RAW.find((r) => r[0] === state.sdYear) || ['', 0, []];
    const rows = sel[2];
    const max = state.sdScale === 'fixed' ? SD_FIXED_MAX : Math.max(...rows.map((r) => r[1]));
    const n = rows.length;
    const bars = rows.map(([label, count], i) => {
      const pct = ((count / max) * 100).toFixed(2);
      const fill = `rgba(255,255,255,${(0.92 - (i / Math.max(n - 1, 1)) * 0.6).toFixed(3)})`;
      return `<div class="hrow hbar" data-tip="${barTip(label, count + ' papers')}">
        <div class="hbar-label">${esc(label)}</div>
        <div class="hbar-track"><div class="hbar-fill" style="width:${pct}%;background:${fill};animation-delay:${i * 30}ms"></div></div>
        <div class="hbar-value">${fmt(count)}</div>
      </div>`;
    }).join('');
    return `<div class="drill">
      <div class="drill-head">
        <div class="drill-hint">↑↓ to change year · hover bars for exact values</div>
        <div class="drill-scale">
          <div class="drill-scale-btn${state.sdScale === 'fixed' ? ' active' : ''}" data-scale="fixed">FIXED</div>
          <div class="drill-scale-btn${state.sdScale === 'relative' ? ' active' : ''}" data-scale="relative">RELATIVE</div>
        </div>
      </div>
      <div class="drill-grid">
        <div class="drill-years">${yearRows}</div>
        <div class="drill-detail">
          <div class="drill-detail-head">
            <span class="drill-sel-year">${state.sdYear}</span>
            <span class="drill-sel-n">n=${fmt(sel[1])} safety papers</span>
          </div>
          <div class="hgrp hbars">${bars}</div>
        </div>
      </div>
      <div class="drill-note">FIXED scales all years to the all-time max (${SD_FIXED_MAX}) so growth reads honestly across years; RELATIVE scales to each year's own max to show internal composition.</div>
    </div>`;
  }

  /* ---------- paper explorer ---------- */
  const px = { q: '', venue: 'all', year: 'all', sd: 'all', shown: 100, open: null };
  let papersData = null, papersLoading = false;
  let detailsData = null, detailsLoading = false;
  const VENUE_LABEL = { iclr: 'ICLR', icml: 'ICML', neurips: 'NeurIPS' };
  const paperUrl = (u) => (u.startsWith('http') ? u : 'https://openreview.net/forum?id=' + u);

  function mkExplorer() {
    if (!papersData) {
      if (!papersLoading) {
        papersLoading = true;
        fetch('data/papers.json')
          .then((r) => r.json())
          .then((d) => { papersData = d; if (state.view === 'papers') renderPanel(); })
          .catch(() => { papersLoading = false; });
      }
      return `<div class="px-loading">LOADING 2,328 PAPERS…</div>`;
    }
    const years = [...new Set(papersData.map((p) => p[2]))].sort((a, b) => b - a);
    const sds = [...new Set(papersData.map((p) => p[3]))].sort();
    const opt = (v, label, cur) => `<option value="${v}"${String(v) === String(cur) ? ' selected' : ''}>${label}</option>`;
    return `<div>
      <div class="px-controls">
        <input class="px-input" id="px-q" type="search" placeholder="Search titles…" aria-label="Search paper titles" value="${esc(px.q)}">
        <select class="px-select" id="px-venue" aria-label="Filter by venue">${opt('all', 'ALL VENUES', px.venue)}${Object.keys(VENUE_LABEL).map((v) => opt(v, VENUE_LABEL[v].toUpperCase(), px.venue)).join('')}</select>
        <select class="px-select" id="px-year" aria-label="Filter by year">${opt('all', 'ALL YEARS', px.year)}${years.map((y) => opt(y, y, px.year)).join('')}</select>
        <select class="px-select" id="px-sd" aria-label="Filter by subdomain">${opt('all', 'ALL SUBDOMAINS', px.sd)}${sds.map((s) => opt(s, s.toUpperCase(), px.sd)).join('')}</select>
      </div>
      <div class="px-count" id="px-count"></div>
      <div id="px-results"></div>
      <div class="px-foot">Score = safety-relevance (1–7) assigned by the classifier. Raw CSVs for every conference-year are in <a href="${GH_URL}/tree/main/data" target="_blank" rel="noopener">the repository</a>.</div>
    </div>`;
  }

  function pxFilter() {
    const q = px.q.trim().toLowerCase();
    const out = [];
    papersData.forEach((p, idx) => {
      if ((px.venue === 'all' || p[1] === px.venue) &&
        (px.year === 'all' || String(p[2]) === String(px.year)) &&
        (px.sd === 'all' || p[3] === px.sd) &&
        (!q || p[0].toLowerCase().includes(q))) out.push(idx);
    });
    return out;
  }

  function pxDetail(idx) {
    if (!detailsData) return `<div class="px-detail px-detail-loading">LOADING CLASSIFIER REASONING…</div>`;
    const [mo, me, ev, conf, reason] = detailsData[idx];
    return `<div class="px-detail">
      <div class="px-detail-scores">
        <span>MOTIVATION ${mo} / 3</span><span>METHODOLOGY ${me} / 2</span><span>EVALUATION ${ev} / 2</span><span>CONFIDENCE ${esc(conf.toUpperCase())}</span>
      </div>
      <div class="px-detail-reason">${esc(reason)}</div>
      <div class="px-detail-note">The classifier's verbatim justification for this label — every classification on this site can be audited this way.</div>
    </div>`;
  }

  function pxUpdate() {
    if (!papersData || state.view !== 'papers') return;
    const rows = pxFilter();
    $('px-count').textContent = fmt(rows.length) + (rows.length === 1 ? ' paper matches' : ' papers match') + ' · click a row for the classifier’s reasoning';
    const slice = rows.slice(0, px.shown);
    $('px-results').innerHTML = `<div class="px-table">` + slice.map((idx) => {
      const [t, venue, year, sd, score, u] = papersData[idx];
      const open = px.open === idx;
      return `<div class="px-rowwrap${open ? ' open' : ''}">
        <div class="px-row" data-idx="${idx}" role="button" tabindex="0" aria-expanded="${open}">
          <a class="px-title" href="${paperUrl(u)}" target="_blank" rel="noopener">${esc(t)}</a>
          <span class="px-meta">${VENUE_LABEL[venue]} ${year}</span>
          <span class="px-meta px-sd"${GLOSSARY[sd] ? ` data-tip="<span class='tt-em'>${esc(sd)}</span><br><span class='tt-dim'>${esc(GLOSSARY[sd])}</span>"` : ''}>${esc(sd)}</span>
          <span class="px-score" data-tip="Safety-relevance score ${score} / 7">${score}</span>
          <span class="px-caret">${open ? '−' : '+'}</span>
        </div>
        ${open ? pxDetail(idx) : ''}
      </div>`;
    }).join('') + `</div>` +
      (rows.length > px.shown ? `<div class="px-more" id="px-more" role="button" tabindex="0">SHOW 100 MORE · ${fmt(rows.length - px.shown)} REMAINING</div>` : '');

    $('px-results').querySelectorAll('.px-row').forEach((el) => {
      const toggle = (e) => {
        if (e.target.closest('a')) return;
        const idx = parseInt(el.dataset.idx, 10);
        px.open = px.open === idx ? null : idx;
        if (px.open !== null && !detailsData && !detailsLoading) {
          detailsLoading = true;
          fetch('data/details.json')
            .then((r) => r.json())
            .then((d) => { detailsData = d; pxUpdate(); })
            .catch(() => { detailsLoading = false; });
        }
        pxUpdate();
      };
      el.addEventListener('click', toggle);
      el.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggle(e); } });
    });
    const more = $('px-more');
    if (more) {
      const showMore = () => { px.shown += 100; pxUpdate(); };
      more.addEventListener('click', showMore);
      more.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); showMore(); } });
    }
  }

  function pxBind() {
    if (!papersData) return;
    $('px-q').addEventListener('input', (e) => { px.q = e.target.value; px.shown = 100; pxUpdate(); });
    [['px-venue', 'venue'], ['px-year', 'year'], ['px-sd', 'sd']].forEach(([id, key]) => {
      $(id).addEventListener('change', (e) => { px[key] = e.target.value; px.shown = 100; px.open = null; pxUpdate(); });
    });
    pxUpdate();
  }

  function mkMethod() {
    return `<div>
      <div class="pipeline">${PIPELINE.map((p) =>
        `<div class="pipe-step"><div class="pipe-step-k">${p.step}</div><div class="pipe-step-name">${esc(p.name)}</div><div class="pipe-step-desc">${p.desc}</div></div>`).join('')}</div>
      <div class="classes-title">FOUR MAJOR CLASSES</div>
      <div class="classes">${CLASS_DEFS.map((c) =>
        `<div class="class-row"><div class="class-n">${c.n}</div><div class="class-name">${esc(c.name)}</div><div class="class-desc">${c.desc}</div></div>`).join('')}</div>
      <div class="method-cite">Full classification rubric — the four classes, 17 safety subdomains, and the 1–7 relevance score with its three axes — is open source: <a href="${GH_URL}/blob/main/src/prompt.txt" target="_blank" rel="noopener">src/prompt.txt</a>.</div>
    </div>`;
  }

  /* ---------- panel ---------- */
  const FACES = {
    conferences: [['pooled', 'POOLED'], ['venues', 'BY VENUE']],
    subdomains: [['all', 'ICLR 2026'], ['year', 'BY YEAR'], ['trends', 'TRENDS']],
    orgs: [['orgs', 'ALL ORGS'], ['types', 'BY TYPE'], ['byyear', 'BY YEAR']],
  };
  const FACE_KEY = { conferences: 'confFace', subdomains: 'sdFace', orgs: 'orgFace' };
  const FACE_META = {
    'subdomains:year': ['Subdomains per year', 'all venues pooled · 2019–2026'],
    'subdomains:trends': ['Subdomain composition over time', "share of each year's safety papers · pooled"],
    'conferences:venues': ['AI-safety share by venue, by year', 'ICLR · ICML · NeurIPS, separate'],
    'orgs:types': ['Org-backed papers by legal structure', 'n=325 · same verified base'],
    'orgs:byyear': ['Org-backed share of safety papers, by year', 'primary org confirmed · of papers checked'],
  };

  function renderPanel() {
    const v = VIEWS[state.view];
    const isOverview = state.view === 'overview';
    $('hero-section').style.display = isOverview ? '' : 'none';
    $('panel-section').style.display = isOverview ? 'none' : '';
    if (isOverview) { $('panel-left').innerHTML = ''; $('panel-right').innerHTML = ''; return; }
    const face = FACE_KEY[state.view] ? state[FACE_KEY[state.view]] : null;
    const yearFace = state.view === 'subdomains' && face === 'year';
    const trendFace = state.view === 'subdomains' && face === 'trends';
    const venueFace = state.view === 'conferences' && face === 'venues';

    $('panel-left').innerHTML = `
      <div class="pl-kicker">${v.kicker}</div>
      <div class="pl-bigrow"><div class="pl-big">${fmtBig(v.big, state.p)}</div><div class="pl-bigunit">${v.bigUnit}</div></div>
      <div class="pl-biglabel">${v.bigLabel}</div>
      <div class="pl-brief">${v.brief}</div>
      <div class="pl-stats">${v.stats.map((s) =>
        `<div class="pl-stat"><span class="pl-stat-k">${s.k}</span><span class="pl-stat-v">${s.v}</span></div>`).join('')}</div>`;

    let chartTitle = v.chartTitle, chartUnit = v.chartUnit;
    const fm = FACE_META[state.view + ':' + face];
    if (fm) { chartTitle = fm[0]; chartUnit = fm[1]; }
    const defs = FACES[state.view];
    const faceBtn = defs ? `<div class="pr-faces">` + defs.map(([k, label]) =>
      `<div class="pr-face${face === k ? ' active' : ''}" data-face="${k}" role="button" tabindex="0" aria-pressed="${face === k}">${label}</div>`).join('') + `</div>` : '';

    let body = '';
    if (yearFace) body = mkDrill();
    else if (trendFace) body = mkTrends();
    else if (venueFace) body = mkVenues();
    else if (v.type === 'orgs') body = mkOrgs();
    else if (v.type === 'hbar') body = mkHbars(v.entries);
    else if (v.type === 'vbar') body = mkVbars(v.entries, v.suf || '', v.note);
    else if (v.type === 'line') body = mkLine();
    else if (v.type === 'papers') body = mkExplorer();
    else if (v.type === 'method') body = mkMethod();

    $('panel-right').innerHTML = `
      <div class="pr-head"><div class="pr-title">${chartTitle}</div><div class="pr-unit">${chartUnit}</div>${faceBtn}</div>
      ${body}`;

    if (v.type === 'line') attachLineHover();
    if (v.type === 'papers') pxBind();

    $('panel-right').querySelectorAll('.pr-face').forEach((el) => {
      const apply = () => {
        const fk = FACE_KEY[state.view];
        if (state[fk] !== el.dataset.face) { state[fk] = el.dataset.face; renderPanel(); }
      };
      el.addEventListener('click', apply);
      el.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); apply(); } });
    });
    $('panel-right').querySelectorAll('.drill-year').forEach((el) =>
      el.addEventListener('click', () => { if (el.dataset.year !== state.sdYear) { state.sdYear = el.dataset.year; renderPanel(); } }));
    $('panel-right').querySelectorAll('.drill-scale-btn').forEach((el) =>
      el.addEventListener('click', () => { if (el.dataset.scale !== state.sdScale) { state.sdScale = el.dataset.scale; renderPanel(); } }));
  }

  /* ---------- disclosure ---------- */
  function renderDisclosure() {
    const v = VIEWS[state.view];
    const root = $('disclosure');
    if (!v.notable) { root.innerHTML = ''; return; }
    const body = state.expanded ? `
      <div class="disc-body">
        <div class="disc-kicker">HIGHEST-SCORING PAPERS · 7 / 7 · SELECTED FROM ${(v.countLabel || 'the safety set').toUpperCase()}</div>
        <div class="disc-grid">${v.notable.map((p) =>
          `<div class="disc-paper"><div class="disc-paper-t">${p.u ? `<a href="${p.u}" target="_blank" rel="noopener">${esc(p.t)}</a>` : esc(p.t)}</div><div class="disc-paper-d">${esc(p.d)}</div></div>`).join('')}</div>
        <div class="disc-foot">Titles, subdomains, and scores are the model's own classification output. The full 412-paper table and all 5,352 raw classifications live in the repository.</div>
      </div>` : '';
    root.innerHTML = `
      <div class="disc-toggle" id="disc-toggle">
        <span>${state.expanded ? 'HIDE PAPERS' : 'SHOW NOTABLE PAPERS'}</span>
        <span class="disc-icon">${state.expanded ? '—' : '+'}</span>
      </div>${body}`;
    $('disc-toggle').addEventListener('click', () => { state.expanded = !state.expanded; renderDisclosure(); });
  }

  /* ---------- feedback ---------- */
  const FB_TYPES = [
    { key: 'feature', glyph: '↗', label: 'FEATURE REQUEST', ac: '#7ca8ff' },
    { key: 'bug', glyph: '✕', label: 'BUG REPORT', ac: '#f87171' },
    { key: 'data', glyph: '±', label: 'DATA ADDITION / FIX', ac: '#4ade80' },
  ];
  const FB_SEVS = [
    { key: 'low', label: 'LOW', ac: '#d4c05a' },
    { key: 'medium', label: 'MEDIUM', ac: '#e09b4d' },
    { key: 'high', label: 'HIGH', ac: '#f87171' },
  ];
  const fbState = { open: false, type: null, sev: null, sending: false };
  let toastTimer = null;

  function fbOpen() {
    if (fbState.open) return;
    fbState.open = true; fbState.type = null; fbState.sev = null; fbState.sending = false;
    $('fb-root').innerHTML = `
      <div class="fb-overlay" id="fb-overlay">
        <div class="fbmodal" role="dialog" aria-modal="true" aria-label="Feedback form">
          <div class="fb-head">
            <div class="fb-title">SEND FEEDBACK</div>
            <div class="fb-close" id="fb-close" role="button" aria-label="Close">✕</div>
          </div>
          <div class="fb-types">${FB_TYPES.map((t) =>
            `<div class="fb-type" data-type="${t.key}" role="button" aria-label="${t.label}">
              <div class="fb-type-edge"></div>
              <div class="fb-type-glyph">${t.glyph}</div>
              <div class="fb-type-label">${t.label}</div>
            </div>`).join('')}</div>
          <input class="fb-input" id="fb-title-in" placeholder="Brief summary…" aria-label="Feedback title" maxlength="150">
          <div class="fb-count fb-title-count" id="fb-title-count">0 / 150</div>
          <textarea class="fb-textarea" id="fb-desc-in" rows="4" placeholder="Describe it — what happened, what you expected, or the data to add…" aria-label="Feedback description" maxlength="500"></textarea>
          <div class="fb-count" id="fb-desc-count">0 / 500</div>
          <div class="fb-sev-wrap" id="fb-sev-wrap" style="display:none">
            <div class="fb-sev-label">SEVERITY</div>
            <div class="fb-sevs">${FB_SEVS.map((s) =>
              `<div class="fb-sev" data-sev="${s.key}" role="button" aria-label="Severity ${s.label}">${s.label}</div>`).join('')}</div>
          </div>
          <div class="fb-submit" id="fb-submit" role="button" aria-label="Submit feedback">OPEN GITHUB ISSUE</div>
          <div class="fb-hint">Submitting opens a prefilled issue on GitHub — that's where feedback is tracked.</div>
        </div>
      </div>`;

    const overlay = $('fb-overlay');
    overlay.addEventListener('click', (e) => { if (e.target === overlay) fbClose(); });
    $('fb-close').addEventListener('click', fbClose);
    overlay.querySelectorAll('.fb-type').forEach((el) => el.addEventListener('click', () => {
      fbState.type = el.dataset.type;
      overlay.querySelectorAll('.fb-type').forEach((o) => {
        const t = FB_TYPES.find((x) => x.key === o.dataset.type);
        const on = o.dataset.type === fbState.type;
        o.classList.toggle('on', on);
        o.style.borderColor = on ? t.ac : 'rgba(255,255,255,.14)';
        o.querySelector('.fb-type-edge').style.background = on ? t.ac : 'transparent';
      });
      $('fb-sev-wrap').style.display = fbState.type === 'bug' ? '' : 'none';
      fbPaintSubmit();
    }));
    overlay.querySelectorAll('.fb-sev').forEach((el) => el.addEventListener('click', () => {
      fbState.sev = el.dataset.sev;
      overlay.querySelectorAll('.fb-sev').forEach((o) => {
        const s = FB_SEVS.find((x) => x.key === o.dataset.sev);
        const on = o.dataset.sev === fbState.sev;
        o.classList.toggle('on', on);
        o.style.borderColor = on ? s.ac : 'rgba(255,255,255,.14)';
        o.style.color = on ? s.ac : '#8a8a8a';
      });
    }));
    $('fb-title-in').addEventListener('input', (e) => {
      $('fb-title-count').textContent = e.target.value.length + ' / 150';
      fbPaintSubmit();
    });
    $('fb-desc-in').addEventListener('input', (e) => {
      $('fb-desc-count').textContent = e.target.value.length + ' / 500';
      fbPaintSubmit();
    });
    $('fb-submit').addEventListener('click', fbSubmit);
  }
  function fbCanSubmit() {
    return !!(fbState.type && $('fb-title-in').value.trim() && $('fb-desc-in').value.trim());
  }
  function fbPaintSubmit() {
    $('fb-submit').classList.toggle('ready', fbCanSubmit() && !fbState.sending);
  }
  function fbClose() {
    fbState.open = false; fbState.sending = false;
    $('fb-root').innerHTML = '';
  }
  function fbSubmit() {
    if (!fbCanSubmit() || fbState.sending) return;
    fbState.sending = true;
    const typeLabel = { feature: 'Feature request', bug: 'Bug report', data: 'Data addition / fix' }[fbState.type];
    const title = `[${typeLabel}] ${$('fb-title-in').value.trim()}`;
    const bodyLines = [
      $('fb-desc-in').value.trim(),
      '',
      '---',
      `- **Type:** ${typeLabel}`,
    ];
    if (fbState.type === 'bug') bodyLines.push(`- **Severity:** ${fbState.sev || 'low'}`);
    bodyLines.push('- **Via:** website feedback form (' + location.host + ')');
    const url = GH_URL + '/issues/new?title=' + encodeURIComponent(title) + '&body=' + encodeURIComponent(bodyLines.join('\n'));
    window.open(url, '_blank', 'noopener');
    fbClose();
    $('toast-root').innerHTML = `
      <div class="toast" role="status">
        <span class="toast-dot"></span>
        <span class="toast-msg">GITHUB OPENED — submit the prefilled issue to send it.</span>
      </div>`;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { $('toast-root').innerHTML = ''; }, 4000);
  }

  /* ---------- keyboard ---------- */
  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && fbState.open) { fbClose(); return; }
    if (state.view !== 'subdomains') return;
    if (e.key !== 'ArrowUp' && e.key !== 'ArrowDown') return;
    const years = SD_RAW.map((r) => r[0]);
    const i = years.indexOf(state.sdYear);
    const j = e.key === 'ArrowUp' ? Math.max(0, i - 1) : Math.min(years.length - 1, i + 1);
    if (j !== i) { e.preventDefault(); state.sdYear = years[j]; renderPanel(); }
  });

  /* ---------- GitHub stars badge ---------- */
  function fetchStars() {
    fetch('https://api.github.com/repos/' + GH_REPO)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => { if (d && typeof d.stargazers_count === 'number') $('gh-stars').textContent = fmt(d.stargazers_count); })
      .catch(() => { /* badge keeps its fallback label */ });
  }

  /* ---------- glass nav scroll states ---------- */
  const nav = document.querySelector('.tabs-wrap');
  let navState = -1;
  const onNavScroll = () => {
    const y = window.scrollY;
    const s = y >= 150 ? 2 : y >= 20 ? 1 : 0;
    if (s === navState) return;
    navState = s;
    nav.classList.toggle('nav-glass', s >= 1);
    nav.classList.toggle('nav-solid', s === 2);
  };
  window.addEventListener('scroll', onNavScroll, { passive: true });
  onNavScroll();

  /* ---------- init ---------- */
  $('masthead-home').addEventListener('click', () => { window.scrollTo({ top: 0 }); });
  $('fab').addEventListener('click', fbOpen);
  $('fab').addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); fbOpen(); } });
  const initial = location.hash.slice(1);
  if (VIEWS[initial]) state.view = initial;
  ttInit();
  renderHero();
  renderTabs();
  renderPanel();
  renderDisclosure();
  fetchStars();
  animate(1000);
})();
