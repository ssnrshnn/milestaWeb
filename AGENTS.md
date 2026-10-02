# milesta.app: guide for AI agents

This repo is the public website for **Milesta**, a private, local-first life
journal for iPhone, iPad and Mac. The app itself, its design system, the
release process and the owner's house rules are described in the app repo's
guide: `~/Documents/Projects/milesta/AGENTS.md`. Read that one too.

This file and `CLAUDE.md` are listed in `.vercelignore`, so they never deploy.
Keep it that way.

Current as of **2026-10-02**.

## House rules (short version)

- **Language.** Write to the owner (Soner Sahin) in **Turkish**. Code,
  comments and commit messages stay in **English**. In public text, write
  his name **"Soner Sahin"**, never "Şahin".
- **Publishing means deploying.** A push to `main` deploys milesta.app.
  - Work on the branch `site-redesign`.
  - Ship with `git push origin site-redesign:main`. Fast-forward only:
    check with `git merge-base --is-ancestor origin/main HEAD` first.
  - After a push, verify the live site.
- **Committing.** Stage explicit paths (no `git add -A`). Don't switch
  branches in this checkout; it lives in iCloud-synced Documents.
- **Impressum.** It must keep the **Hungen** c/o block verbatim:
  "Soner Sahin / c/o Impressumservice Dein-Impressum / Stettiner Str. 41 /
  35410 Hungen / Deutschland". Contact is email only (info@milesta.app).
  Never publish the provider's Hanau address or the owner's home address.
  Don't edit the legal text without asking.

## Structure

- **English sources** live at the root: `index.html`, `support.html`,
  `privacy.html`, `terms.html` and `press.html`.
  - `impressum.html` is the single German page for everyone.
  - `404.html` is used by every language.
- **Generated pages:** `/<code>/…` for de, es, fr, pt-br, ru, tr, ar, ur, hi,
  bn, ja, zh-hans, id and vi. They are **generated; never edit them by hand.**
- **Styles and scripts:** `wrapped.css` and `wrapped.js` (no dependencies).
  Every page uses the app's **Wrapped** design: night sky, gradient type,
  glass panels. Text pages use `body.doc-page` with a frosted `.doc` panel.
- **Assets:**
  - `assets/wrapped/*.webp`: showcase images (posters, monthly cards,
    phone shots, photo chips). They're rendered from the real app, and
    width/height must stay as declared in the HTML.
  - `assets/og/og-<code>.jpg` and `assets/og-image.png`: social cards, built
    with `scripts/make_og_images.mjs` from `scripts/og-card.html`. The script
    needs `puppeteer-core`; run it from a folder that has `node_modules` and
    set `SITE=<this repo>`.
  - `assets/press/`:
    - `full/*.png` and `thumb/*.jpg`: thumbnails are 720 px tall.
    - `milesta-press-kit.zip`, currently 28 MB. Its size appears in the
      download label in every language; update it if the zip changes.
- **Other files:** `sitemap.xml` and `robots.txt`; `vercel.json` sets
  `cleanUrls: true` and `trailingSlash: false`.

## Translations: `i18n/`

Full workflow is in `i18n/README.md`. The essentials:

```
python3 i18n/build.py extract   # after changing English copy
python3 i18n/build.py check     # missing / stale / malformed per language
python3 i18n/build.py build     # writes /<code>/…, 404 texts, sitemap
```

- `i18n/source.json` holds every string, keyed by `sha1(English text)[:12]`.
  Inline markup becomes numbered tags (`<0>…</0>`).
  - Changing an English sentence creates a **new key**. Move each language's
    translation to the new key: a small Python script editing
    `i18n/strings/<code>.json` works.
  - Write those files with `json.dumps(…, ensure_ascii=False, indent=1)` and a
    trailing newline; that round-trips them byte for byte.
- `translate="no"` or `data-i18n="skip"` keeps an element out of
  translation. "Milesta" is never translated.
- **Glossary.** The app's own translations are the glossary: design,
  palette, screen and setting names must match the app in each language.
- **Legal pages.** Translated privacy and terms pages carry a note linking
  to the English original.
- **Sitemap dates.** The sitemap's `lastmod` comes from git history, so
  build again after committing.

## SEO and analytics

- **Metadata.** Every page has its own title and description per language,
  plus `canonical` and `hreflang`.
- **Structured data.** The home page has JSON-LD (`WebSite` +
  `MobileApplication`). The author is `Person` "Soner Sahin" with
  `url: https://ssnrshnn.com`.
- **App Store links.** Always use `https://apps.apple.com/app/id6791968029`
  and the official badge `assets/app-store-badge.svg`.
- **Developer credit.** Every footer has a localized "Made by Soner Sahin"
  linking to https://ssnrshnn.com (`rel="author"`). The press factsheet links
  there too. Keep it quiet; the owner didn't want it prominent.
- **App name.** The press factsheet shows each storefront's App Store name
  for its language, e.g. "Milesta: Life Journal Timeline" in English and
  "Milesta: Tagebuch & Rückblick" in German.
- **Analytics.** PostHog runs cookieless (`cookieless_mode: 'always'`)
  through a proxy, so no consent banner is needed. Vercel Speed Insights is
  on as well. Local previews should strip both.

## Testing before a deploy

There is no test suite in this repo. The checks that worked used
puppeteer-core with system Chrome against a local preview (`npx serve` with
clean URLs):

- **Every page × several widths** (320, 390, 768 and 1280 px, plus 15
  languages for the home page): no console errors, failed requests, broken
  images or missing alt text, and no horizontal overflow.
- **Bento tiles:** copy never sits under a phone, the four design phones are
  equal, and nothing is clipped. Same for the Premium card: its peeking
  posters never cover the list.
- **Look at screenshots** of what changed, including RTL (ar, ur) and a
  narrow phone width.

## Content rules learned the hard way

- When the app and the site feel different, adapt the **app** to the site,
  never the site to the app.
- Images come from the real app with **our own sample photos**. These are
  self-generated, Apache-2.0, and listed in the app guide. Never use stock
  or scraped photos.
- No "coming in the next update" pills and no "made with sample data"
  notes; the owner removed both.
- The privacy policy states that backups are optional and go to the user's
  own iCloud Drive, that purchases go through RevenueCat, and that analytics
  are opt-in. Keep it honest whenever the app changes.
