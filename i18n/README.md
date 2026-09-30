# Website translations

The English pages at the site root (`index.html`, `support.html`,
`privacy.html`, `terms.html`, `press.html`) are the source. Every other
language is generated into `/<code>/` from them — never edit those folders
by hand.

    python3 i18n/build.py extract   # English copy changed? refresh source.json
    python3 i18n/build.py check     # what is missing / stale / malformed per language
    python3 i18n/build.py build     # write /de/…, /tr/…, the 404 texts, sitemap.xml

- `source.json` — every string, keyed by a hash of its English text, with
  inline markup as numbered tags (`<0>…</0>`, `<1/>`). A changed English
  sentence gets a new key, so `check` shows it as missing everywhere.
- `strings/<code>.json` — `{key: translation}` per language. Tags must come
  back exactly once each; `check` enforces it.
- `months.json` — month initials for the recap art (from `Intl`, Urdu and
  Japanese by hand).
- The app's own translations are the glossary: design, palette, screen and
  setting names must match what people see in the app.

English keeps its URLs (the app and App Store Connect link to /privacy,
/terms, /support). `/impressum` is the German original for everyone.
English pages send first-time visitors to their browser's language; a
choice made in the language menu is remembered on the device
(`localStorage["milesta-lang"]`) and wins from then on.
