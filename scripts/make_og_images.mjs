// Social cards (1200×630) for every language, from scripts/og-card.html and
// the headline of each built home page. Run after `python3 i18n/build.py build`:
//
//   npm i puppeteer-core   (anywhere on NODE_PATH)
//   node scripts/make_og_images.mjs
//
// Writes assets/og/og-<code>.jpg; English also refreshes assets/og-image.png.
import puppeteer from 'puppeteer-core';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const site = process.env.SITE || path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const chrome = process.env.CHROME || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const codes = ['en', ...fs.readdirSync(path.join(site, 'i18n/strings')).filter((f) => f.endsWith('.json')).map((f) => f.slice(0, -5))];
fs.mkdirSync(path.join(site, 'assets/og'), { recursive: true });

const browser = await puppeteer.launch({ executablePath: chrome, headless: 'new', args: ['--allow-file-access-from-files'] });
for (const code of codes) {
  const home = fs.readFileSync(path.join(site, code === 'en' ? 'index.html' : `${code}/index.html`), 'utf8');
  const h1 = home.match(/<h1 id="hero-title"[^>]*>([\s\S]*?)<\/h1>/)[1];
  const sub = home.match(/<p class="eyebrow-pill[^"]*"[^>]*>[\s\S]*?<\/span>\s*([\s\S]*?)\s*<\/p>/)[1];
  const lang = home.match(/<html lang="([^"]+)"/)[1];
  const dir = /<html [^>]*dir="rtl"/.test(home) ? 'rtl' : 'ltr';
  const page = await browser.newPage();
  await page.setViewport({ width: 1200, height: 630, deviceScaleFactor: 1 });
  await page.goto('file://' + path.join(site, 'scripts/og-card.html'), { waitUntil: 'networkidle0' });
  await page.evaluate(({ h1, sub, lang, dir }) => {
    const d = document.documentElement;
    d.lang = lang; d.dir = dir;
    const h = document.getElementById('headline');
    h.innerHTML = h1;
    document.getElementById('sub').innerHTML = sub;
    // Longer languages: shrink the headline until it fits its column.
    let size = 76;
    while (size > 40 && (h.scrollWidth > 620 || h.offsetHeight > 300)) { size -= 2; h.style.fontSize = size + 'px'; }
  }, { h1, sub, lang, dir });
  await new Promise((r) => setTimeout(r, 150));
  const out = path.join(site, `assets/og/og-${code}.jpg`);
  await page.screenshot({ path: out, type: 'jpeg', quality: 88 });
  if (code === 'en') await page.screenshot({ path: path.join(site, 'assets/og-image.png') });
  console.log(code, fs.statSync(out).size, 'bytes');
  await page.close();
}
await browser.close();
