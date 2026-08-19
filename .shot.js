// puppeteer-core screenshot driver using local Chrome
const puppeteer = require('C:\\Users\\12421\\.workbuddy\\tmp\\neon-shots\\node_modules\\puppeteer-core');
const fs = require('fs');
const path = require('path');

const URL = process.argv[2] || 'http://localhost:8917/index.html';
const OUTDIR = process.argv[3] || '';
const W = parseInt(process.argv[4] || '2560', 10);
const H = parseInt(process.argv[5] || '960', 10);
const PAGES = (process.argv[6] || '1-18').split(',').map(s => {
  const m = s.match(/^(\d+)(?:-(\d+))?$/);
  if (!m) return [];
  const a = parseInt(m[1], 10), b = m[2] ? parseInt(m[2], 10) : a;
  const arr = [];
  for (let i = a; i <= b; i++) arr.push(i);
  return arr;
}).flat();

if (!OUTDIR) { console.error('OUTDIR required'); process.exit(2); }
fs.mkdirSync(OUTDIR, { recursive: true });

(async () => {
  const browser = await puppeteer.launch({
    executablePath: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    headless: 'new',
    args: ['--no-sandbox','--disable-setuid-sandbox','--disable-dev-shm-usage','--disable-gpu','--font-render-hinting=none','--hide-scrollbars']
  });
  try {
    const page = await browser.newPage();
    await page.setViewport({ width: W, height: H, deviceScaleFactor: 1 });
    for (const idx of PAGES) {
      if (idx < 1) continue;
      const slideUrl = URL + (URL.includes('?') ? '&' : '?') + 'slide=' + idx;
      try {
        await page.goto(slideUrl, { waitUntil: 'domcontentloaded', timeout: 45000 });
        // wait for motion library (ESM) to load
        await page.waitForFunction(() => !!document.body.classList.contains('motion-ready') || !!document.querySelector('[data-anim]'), { timeout: 8000 }).catch(()=>{});
      } catch (e) {
        console.error('goto failed', slideUrl, e.message);
        continue;
      }
      // disable autoplay timers/loops
      await page.evaluate(() => {
        try {
          if (window.autoplayTimer) clearInterval(window.autoplayTimer);
          // clear all setIntervals & timeouts (best-effort)
          const _si = window.setInterval;
          window.setInterval = function(fn, t){ if(t<500) return 0; return _si(fn,t); };
          window.__pausedForShot = true;
        } catch(e){}
      });
      // wait for animations + fonts (force-show any hidden data-anim as safety)
      await page.evaluate(() => {
        document.querySelectorAll('[data-anim], .h-xl, .h-hero, .h-sub, .stat-nb, .step').forEach(el => {
          el.style.setProperty('opacity', '1', 'important');
          el.style.setProperty('transform', 'none', 'important');
          el.style.setProperty('filter', 'none', 'important');
        });
        // diagnostic: log h-xl computed style
        const xls = document.querySelectorAll('.slide.active .h-xl');
        if (xls[0]) {
          const cs = getComputedStyle(xls[0]);
          window.__dbg = {
            rect: xls[0].getBoundingClientRect(),
            computed: {
              fontSize: cs.fontSize,
              lineHeight: cs.lineHeight,
              opacity: cs.opacity,
              transform: cs.transform,
              filter: cs.filter,
              marginTop: cs.marginTop,
              paddingTop: cs.paddingTop
            },
            frameRect: xls[0].parentElement.getBoundingClientRect(),
            framePad: getComputedStyle(xls[0].parentElement).paddingTop
          };
        }
      });
      // wait for animations + fonts
      await new Promise(r => setTimeout(r, 3000));
      const out = path.join(OUTDIR, `p${String(idx).padStart(2,'0')}_${W}x${H}.png`);
      await page.screenshot({ path: out, fullPage: false, type: 'png' });
      console.log('saved', out);
      const dbg = await page.evaluate(() => window.__dbg);
      if (dbg) console.log('DBG', JSON.stringify(dbg, null, 2));
      // also dump all .frame children positions
      const frames = await page.evaluate(() => {
        const f = document.querySelector('.slide.active .frame');
        if (!f) return null;
        return [...f.children].map((c, i) => {
          const r = c.getBoundingClientRect();
          const cs = getComputedStyle(c);
          return {
            i, tag: c.tagName, cls: c.className, text: (c.textContent||'').trim().slice(0,30),
            top: Math.round(r.top), bottom: Math.round(r.bottom), height: Math.round(r.height),
            opacity: cs.opacity, transform: cs.transform, filter: cs.filter
          };
        });
      });
      if (frames) console.log('FRAME:', JSON.stringify(frames, null, 2));
    }
  } finally {
    await browser.close();
  }
})().catch(e => { console.error('ERR', e); process.exit(1); });