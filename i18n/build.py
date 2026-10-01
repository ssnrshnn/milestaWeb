#!/usr/bin/env python3
"""Milesta website localisation (standard library only).

The English pages at the site root are the source of truth. This script

  extract   collects every translatable string of those pages into
            i18n/source.json (text with inline markup turned into numbered
            tags like <0>…</0> and <1/>, plus alt/aria-label/meta texts);
  build     writes /<lang>/<page>.html for every language that has
            i18n/strings/<lang>.json, and refreshes the generated blocks in
            the English pages too (language menu, hreflang links, the
            language detection script), the localised 404 texts and the
            sitemap;
  check     reports missing, stale or malformed translations.

English keeps its URLs (/, /privacy, …): the app and App Store Connect link
to them. The Impressum stays the single German original for everyone.
"""

import hashlib
import html
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
I18N = SITE / 'i18n'
ORIGIN = 'https://milesta.app'

# source file -> URL slug ('' is the home page)
PAGES = {
    'index.html': '',
    'support.html': 'support',
    'privacy.html': 'privacy',
    'terms.html': 'terms',
    'press.html': 'press',
}
LEGAL = {'privacy.html', 'terms.html'}

# (url code, html lang, endonym, og:locale, direction) — the app's 15 languages
LANGS = [
    ('en', 'en', 'English', 'en_US', 'ltr'),
    ('de', 'de', 'Deutsch', 'de_DE', 'ltr'),
    ('es', 'es', 'Español', 'es_ES', 'ltr'),
    ('fr', 'fr', 'Français', 'fr_FR', 'ltr'),
    ('pt-br', 'pt-BR', 'Português (Brasil)', 'pt_BR', 'ltr'),
    ('ru', 'ru', 'Русский', 'ru_RU', 'ltr'),
    ('tr', 'tr', 'Türkçe', 'tr_TR', 'ltr'),
    ('ar', 'ar', 'العربية', 'ar_AR', 'rtl'),
    ('ur', 'ur', 'اردو', 'ur_PK', 'rtl'),
    ('hi', 'hi', 'हिन्दी', 'hi_IN', 'ltr'),
    ('bn', 'bn', 'বাংলা', 'bn_BD', 'ltr'),
    ('ja', 'ja', '日本語', 'ja_JP', 'ltr'),
    ('zh-hans', 'zh-Hans', '简体中文', 'zh_CN', 'ltr'),
    ('id', 'id', 'Bahasa Indonesia', 'id_ID', 'ltr'),
    ('vi', 'vi', 'Tiếng Việt', 'vi_VN', 'ltr'),
]
BY_CODE = {l[0]: l for l in LANGS}

# Strings the build itself needs, translated like any other unit.
EXTRA = {
    'x-language': ('Language', 'Label of the language menu button (screen readers) — one word.'),
    'x-legal-note': ('This translation is here for your convenience. If it differs from the <0>English original</0>, the English version applies.',
                     'Shown at the top of the translated Privacy Policy and Terms of Use. <0>…</0> is a link to the English page.'),
    'x-404-title': ('This page took a <0>different path.</0>', '404 page headline. <0>…</0> is the part set in the gradient.'),
    'x-404-lead': ('The link may be old, or the page moved. Everything else is where you left it.', '404 page, line under the headline.'),
    'x-404-home': ('Back to Milesta', '404 page button to the home page.'),
    'x-404-support': ('Support', '404 page button to the support page (same word as the Support page in the menu).'),
    'x-404-doc-title': ('Page not found — Milesta', '404 page <title>.'),
}

VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'source', 'track', 'wbr'}
INLINE = {'a', 'abbr', 'b', 'bdi', 'bdo', 'br', 'cite', 'code', 'em', 'i', 'img', 'kbd', 'mark', 'q', 's',
          'small', 'span', 'strong', 'sub', 'sup', 'time', 'u', 'wbr', 'svg'}
OPAQUE = {'svg', 'script', 'style', 'template'}
TRANS_ATTRS = ('alt', 'aria-label', 'title', 'placeholder', 'data-alt-gallery', 'data-alt-path')
META_KEYS = {('name', 'description'), ('property', 'og:title'), ('property', 'og:description'),
             ('name', 'twitter:title'), ('name', 'twitter:description')}
TAGLINE = 'Your life, one milestone at a time.'   # the social card's alt text is built from it
DNT = {'Milesta'}   # "Milesta Premium" is translated: several languages localise Premium


# ---------------------------------------------------------------- parsing

class Node:
    __slots__ = ('tag', 'attrs', 'start', 'open_end', 'close_start', 'end', 'children', 'parent', 'text')

    def __init__(self, tag, attrs, start, open_end, parent):
        self.tag, self.attrs, self.start, self.open_end = tag, attrs, start, open_end
        self.close_start = self.end = open_end
        self.children, self.parent, self.text = [], parent, None

    def attr(self, name):
        for k, v in self.attrs:
            if k == name:
                return v
        return None


class Text:
    __slots__ = ('start', 'end', 'raw')

    def __init__(self, start, end, raw):
        self.start, self.end, self.raw = start, end, raw


class Tree(HTMLParser):
    def __init__(self, src):
        super().__init__(convert_charrefs=False)
        self.src = src
        self.lines = [0] + [i + 1 for i, c in enumerate(src) if c == '\n']
        self.root = Node('#root', [], 0, 0, None)
        self.stack = [self.root]
        self.feed(src)
        self.close()
        self.root.close_start = self.root.end = len(src)

    def _abs(self):
        line, col = self.getpos()
        return self.lines[line - 1] + col

    def handle_starttag(self, tag, attrs):
        pos = self._abs()
        raw = self.get_starttag_text()
        node = Node(tag, attrs, pos, pos + len(raw), self.stack[-1])
        self.stack[-1].children.append(node)
        if tag not in VOID and not raw.endswith('/>'):
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        pos = self._abs()
        raw = self.get_starttag_text()
        self.stack[-1].children.append(Node(tag, attrs, pos, pos + len(raw), self.stack[-1]))

    def handle_endtag(self, tag):
        pos = self._abs()
        end = self.src.index('>', pos) + 1
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                for node in self.stack[i:]:
                    node.close_start, node.end = pos, end
                del self.stack[i:]
                return

    def _text(self, raw):
        pos = self._abs()
        self.stack[-1].children.append(Text(pos, pos + len(raw), raw))

    def handle_data(self, data):
        self._text(data)

    def handle_entityref(self, name):
        self._text(f'&{name};')

    def handle_charref(self, name):
        self._text(f'&#{name};')


def has_block(node):
    for c in node.children:
        if isinstance(c, Node) and c.tag not in OPAQUE and (c.tag not in INLINE or has_block(c)):
            return True
    return False


def is_inline(item):
    if isinstance(item, Text):
        return True
    return item.tag in OPAQUE and item.tag == 'svg' or (item.tag in INLINE and not has_block(item))


def visible_text(item):
    if isinstance(item, Text):
        return html.unescape(item.raw)
    if item.tag in OPAQUE:
        return ''
    return ''.join(visible_text(c) for c in item.children)


def skipped(node):
    while node is not None:
        if isinstance(node, Node) and (node.attr('translate') == 'no' or node.attr('data-i18n') == 'skip'):
            return True
        node = node.parent
    return False


def worth_translating(text):
    t = ' '.join(text.split())
    return bool(t) and t not in DNT and re.search(r'[A-Za-z]{2,}', t) is not None


def uid(source):
    return hashlib.sha1(source.encode()).hexdigest()[:12]


class Unit:
    """One translatable range of the page: element content or an attribute value.

    An attribute inside a text unit (a link's title, an inline image's alt)
    is `nested`: it is translated as part of that unit's tags, not spliced
    on its own."""

    def __init__(self, kind, start, end, source, tokens, context):
        self.kind, self.start, self.end, self.source, self.tokens, self.context = kind, start, end, source, tokens, context
        self.nested = False
        # <title> shows its content as plain text: markup there would be
        # read out literally, in the tab and in search results.
        self.plain = False

    @property
    def id(self):
        return uid(self.source)


def run_to_source(items, src):
    """Inline items -> ('text with <0>…</0> tags', {n: (open_src, close_src) | (whole_src, None)})."""
    tokens = {}
    out = []

    def walk(item):
        if isinstance(item, Text):
            out.append(html.unescape(item.raw))
            return
        n = len(tokens)
        if item.tag in OPAQUE or item.tag in VOID:
            tokens[n] = (src[item.start:item.end], None)
            out.append(f'<{n}/>')
            return
        tokens[n] = (src[item.start:item.open_end], src[item.close_start:item.end])
        out.append(f'<{n}>')
        for c in item.children:
            walk(c)
        out.append(f'</{n}>')

    for it in items:
        walk(it)
    text = re.sub(r'\s+', ' ', ''.join(out)).strip()
    return text, tokens


def blank(item):
    """Whitespace, or an element with no words in it (an icon, a swatch)."""
    return not visible_text(item).strip()


def trim(items):
    while items and blank(items[0]):
        items = items[1:]
    while items and blank(items[-1]):
        items = items[:-1]
    return items


# Elements that only hold other elements: side-by-side links in one of them
# (a store badge next to a button) are separate strings, not one sentence.
CONTAINERS = {'div', 'section', 'header', 'footer', 'nav', 'figure', 'main', 'article', 'aside', 'ul', 'ol', 'body', 'details'}


def collect_units(src, page):
    tree = Tree(src)
    units = []

    def context(node):
        bits = [node.tag]
        if node.attr('id'):
            bits.append('#' + node.attr('id'))
        if node.attr('class'):
            bits.append('.' + '.'.join(node.attr('class').split()[:2]))
        return f'{page} {"".join(bits)}'

    def add_run(parent, items):
        items = trim(items)
        if parent.tag in CONTAINERS and sum(isinstance(i, Node) for i in items) > 1 \
                and all(isinstance(i, Node) or not i.raw.strip() for i in items):
            for i in items:
                if isinstance(i, Node):
                    add_run(parent, [i])
            return
        # A run that is one wrapper around everything (<a>, <span>…) gives
        # the translator just the words; the wrapper stays in the page.
        while len(items) == 1 and isinstance(items[0], Node) and items[0].tag in INLINE - VOID - OPAQUE:
            parent = items[0]
            items = trim(list(items[0].children))
        if not items or not worth_translating(''.join(visible_text(i) for i in items)):
            return
        text, tokens = run_to_source(items, src)
        unit = Unit('html', items[0].start, items[-1].end, text, tokens, context(parent))
        unit.plain = parent.tag == 'title'
        units.append(unit)

    def walk(node):
        if isinstance(node, Text) or node.tag in OPAQUE:
            return
        if skipped(node):
            return
        # attributes
        for name in TRANS_ATTRS:
            val = node.attr(name)
            if val and worth_translating(val):
                raw = src[node.start:node.open_end]
                m = re.search(r'\s' + re.escape(name) + r'\s*=\s*"([^"]*)"', raw)
                if m:
                    units.append(Unit('attr', node.start + m.start(1), node.start + m.end(1), ' '.join(html.unescape(m.group(1)).split()), {}, f'{context(node)} @{name}'))
        if node.tag == 'meta':
            for key in META_KEYS:
                if node.attr(key[0]) == key[1]:
                    raw = src[node.start:node.open_end]
                    m = re.search(r'\scontent\s*=\s*"([^"]*)"', raw)
                    units.append(Unit('attr', node.start + m.start(1), node.start + m.end(1), ' '.join(html.unescape(m.group(1)).split()), {}, f'{page} meta {key[1]}'))
        if node.tag not in INLINE or has_block(node):
            run = []
            for c in node.children:
                if is_inline(c):
                    run.append(c)
                else:
                    add_run(node, run)
                    run = []
                    walk(c)
            add_run(node, run)
            # attributes of inline children inside runs
            for c in node.children:
                if isinstance(c, Node) and is_inline(c):
                    walk_attrs_only(c)

    def walk_attrs_only(node):
        if isinstance(node, Text) or node.tag in OPAQUE or skipped(node):
            return
        for name in TRANS_ATTRS:
            val = node.attr(name)
            if val and worth_translating(val):
                raw = src[node.start:node.open_end]
                m = re.search(r'\s' + re.escape(name) + r'\s*=\s*"([^"]*)"', raw)
                if m:
                    units.append(Unit('attr', node.start + m.start(1), node.start + m.end(1), ' '.join(html.unescape(m.group(1)).split()), {}, f'{context(node)} @{name}'))
        for c in node.children:
            walk_attrs_only(c)

    walk(tree.root)
    units.sort(key=lambda u: u.start)
    spans = [(u.start, u.end) for u in units if u.kind == 'html']
    for u in units:
        if u.kind == 'attr' and any(a <= u.start and u.end <= b for a, b in spans):
            u.nested = True
    # overlapping ranges would mean a parsing mistake
    top = [u for u in units if not u.nested]
    for a, b in zip(top, top[1:]):
        assert a.end <= b.start, (page, a.context, b.context)
    return units


# ------------------------------------------------------------ translation

TOKEN = re.compile(r'<(/?)(\d+)(/?)>')


def check_tokens(source, target):
    want = sorted(m.group(0) for m in TOKEN.finditer(source))
    got = sorted(m.group(0) for m in TOKEN.finditer(target))
    if want != got:
        return f'tags differ: expected {want}, got {got}'
    stack = []
    for m in TOKEN.finditer(target):
        close, n, selfclose = m.group(1), m.group(2), m.group(3)
        if selfclose:
            continue
        if not close:
            stack.append(n)
        elif not stack or stack.pop() != n:
            return 'tags are not nested properly'
    if re.search(r'<(?!/?\d+/?>)[a-zA-Z/!]', target):
        return 'contains raw HTML'
    return None


ATTR_IN_TAG = re.compile(r'\s(' + '|'.join(map(re.escape, TRANS_ATTRS)) + r')="([^"]*)"')


def translate_tag(tag_src, strings):
    """Translate the alt/title/aria-label values inside one start tag."""
    def fix(m):
        t = strings.get(uid(' '.join(html.unescape(m.group(2)).split())))
        return f' {m.group(1)}="{html.escape(t)}"' if t else m.group(0)
    return ATTR_IN_TAG.sub(fix, tag_src)


def text_html(text, code=None):
    t = html.escape(text, quote=False)
    if code == 'tr':
        # CSS uppercasing in Turkish turns the brand into "MİLESTA".
        t = t.replace('Milesta', '<span lang="en">Milesta</span>')
    return t


def render(target, tokens, strings=None, code=None):
    """Translated text with <0>…</0> tags -> HTML using the page's own tags."""
    out, pos = [], 0
    for m in TOKEN.finditer(target):
        out.append(text_html(target[pos:m.start()], code))
        n = int(m.group(2))
        open_src, close_src = tokens[n]
        if m.group(1) and not m.group(3):
            out.append(close_src)
        else:
            out.append(translate_tag(open_src, strings) if strings else open_src)
        pos = m.end()
    out.append(text_html(target[pos:], code))
    return ''.join(out)


def load_strings(code):
    p = I18N / 'strings' / f'{code}.json'
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() else None


# ----------------------------------------------------------- generated bits

def url(code, slug):
    if code == 'en':
        return '/' + slug
    return f'/{code}' + (f'/{slug}' if slug else '')


def menu_html(code, slug, strings):
    label = strings.get('x-language', 'Language') if strings else 'Language'
    cur = BY_CODE[code]
    items = []
    for c, lang, name, _, _ in LANGS:
        attrs = f' aria-current="true"' if c == code else ''
        items.append(f'            <li><a href="{url(c, slug)}" hreflang="{lang}" lang="{lang}" data-lang="{c}"{attrs}>{name}</a></li>')
    return (f'<!-- i18n:menu -->\n        <details class="lang-menu" translate="no">\n'
            f'          <summary aria-label="{html.escape(label)}: {cur[2]}"><svg class="lang-globe" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.6 2.4 3.9 5.4 3.9 9s-1.3 6.6-3.9 9M12 3c-2.6 2.4-3.9 5.4-3.9 9s1.3 6.6 3.9 9"/></svg><span>{cur[2]}</span></summary>\n'
            f'          <ul class="lang-list">\n' + '\n'.join(items) + '\n          </ul>\n        </details>\n        <!-- /i18n:menu -->')


DETECT = '''<script>
    (function () {
      /* First visit: follow the browser's languages. A language picked in
         the menu is remembered on this device and wins from then on. */
      var ok = {LIST};
      var saved = null;
      try { saved = localStorage.getItem("milesta-lang"); } catch (e) {}
      if (saved === "en") return;
      var want = ok[saved] ? saved : null;
      if (!want) {
        var list = navigator.languages && navigator.languages.length ? navigator.languages : [navigator.language || ""];
        for (var i = 0; i < list.length; i++) {
          var p = String(list[i]).toLowerCase().split("-")[0];
          if (p === "en") return;
          var c = p === "zh" ? "zh-hans" : p === "pt" ? "pt-br" : p;
          if (ok[c]) { want = c; break; }
        }
      }
      if (want) location.replace("/" + want + "{SLUG}" + location.search + location.hash);
    })();
  </script>'''


def head_block(code, slug):
    lines = ['<!-- i18n:head -->']
    for c, lang, _, _, _ in LANGS:
        lines.append(f'  <link rel="alternate" hreflang="{lang}" href="{ORIGIN}{url(c, slug)}">')
    lines.append(f'  <link rel="alternate" hreflang="x-default" href="{ORIGIN}{url("en", slug)}">')
    for c, _, _, loc, _ in LANGS:
        if c != code:
            lines.append(f'  <meta property="og:locale:alternate" content="{loc}">')
    if code == 'en':
        ok = '{' + ', '.join(f'"{c}": 1' for c, *_ in LANGS if c != 'en') + '}'
        lines.append('  ' + DETECT.replace('{LIST}', ok).replace('{SLUG}', '/' + slug if slug else ''))
    lines.append('  <!-- /i18n:head -->')
    return '\n'.join(lines)


def replace_block(page_src, name, block):
    pat = re.compile(r'<!-- i18n:' + name + r' -->.*?<!-- /i18n:' + name + r' -->', re.S)
    assert pat.search(page_src), f'missing i18n:{name} markers'
    return pat.sub(lambda m: block, page_src, count=1)


# ------------------------------------------------------------------ pages

def localise_links(page, code):
    """Relative links of an English page -> root-absolute links for /<code>/…"""
    def fix(m):
        attr, val = m.group(1), m.group(2)
        if re.match(r'^(https?:|mailto:|#|/|data:)', val):
            return m.group(0)
        name, _, frag = val.partition('#')
        frag = '#' + frag if frag else ''
        if name in PAGES:
            return f'{attr}="{url(code, PAGES[name])}{frag}"'
        if name == 'impressum.html':
            return f'{attr}="/impressum{frag}"'
        return f'{attr}="/{val}"'
    return re.sub(r'\b(href|src)="([^"]*)"', fix, page)


MONTHS = None


def months(code):
    global MONTHS
    if MONTHS is None:
        MONTHS = json.loads((I18N / 'months.json').read_text(encoding='utf-8'))
    return MONTHS[code]


def build_page(name, code, strings, errors):
    slug = PAGES[name]
    src = (SITE / name).read_text(encoding='utf-8')
    units = collect_units(src, name)
    lang = BY_CODE[code]
    edits = []
    for u in units:
        if u.nested:
            continue
        t = strings.get(u.id)
        if t is None:
            errors.append(f'{code}: missing {u.id} ({u.context}): {u.source[:60]}')
            continue
        bad = check_tokens(u.source, t)
        if bad:
            errors.append(f'{code}: {u.id} ({u.context}): {bad}')
            continue
        if u.kind == 'html' and not u.plain:
            edits.append((u.start, u.end, render(t, u.tokens, strings, code)))
        else:
            edits.append((u.start, u.end, html.escape(t, quote=u.kind != 'html')))
    out = src
    for start, end, new in sorted(edits, reverse=True):
        out = out[:start] + new + out[end:]

    out = re.sub(r'<html lang="[^"]*"', f'<html lang="{lang[1]}"' + (' dir="rtl"' if lang[4] == 'rtl' else ''), out, count=1)
    out = localise_links(out, code)
    # Apple's badge in the page's language (where Apple makes one), sized to its own proportions
    badge = SITE / 'assets' / 'badges' / f'app-store-{code}.svg'
    if badge.exists():
        m = re.search(r'<svg[^>]*?\swidth="([\d.]+)"[^>]*?\sheight="([\d.]+)"', badge.read_text(encoding='utf-8'))
        ratio = float(m.group(1)) / float(m.group(2))
        def fix_badge(t):
            tag = t.group(0).replace('/assets/app-store-badge.svg', f'/assets/badges/app-store-{code}.svg')
            h = re.search(r'height="(\d+)"', tag)
            return re.sub(r'width="\d+"', f'width="{round(int(h.group(1)) * ratio)}"', tag) if h else tag
        out = re.sub(r'<img src="/assets/app-store-badge\.svg"[^>]*>', fix_badge, out)
    canon = f'{ORIGIN}{url(code, slug)}'
    out = re.sub(r'(<link rel="canonical" href=")[^"]*(")', r'\g<1>' + canon + r'\2', out)
    out = re.sub(r'(<meta property="og:url" content=")[^"]*(")', r'\g<1>' + canon + r'\2', out)
    out = re.sub(r'(<meta property="og:locale" content=")[^"]*(")', r'\g<1>' + lang[3] + r'\2', out)
    tagline = strings.get(uid(TAGLINE))
    if tagline:
        out = re.sub(r'(<meta property="og:image:alt" content=")[^"]*(")', lambda m: m.group(1) + html.escape('Milesta — ' + tagline) + m.group(2), out)
    if (SITE / 'assets' / 'og' / f'og-{code}.jpg').exists():
        card = f'{ORIGIN}/assets/og/og-{code}.jpg'
        out = re.sub(r'(<meta (?:property="og:image"|name="twitter:image") content=")[^"]*(")', r'\g<1>' + card + r'\2', out)
    out = replace_block(out, 'head', head_block(code, slug))
    out = replace_block(out, 'menu', menu_html(code, slug, strings))
    # the year's month initials in the recap art
    letters = months(code)
    english = months('en')
    def month_art(m):
        svg = m.group(0)
        texts = re.findall(r'<text [^>]*>([^<]*)</text>', svg)
        if texts != english:
            return svg
        count = iter(range(12))
        return re.sub(r'(<text [^>]*>)[^<]*(</text>)', lambda t: f'{t.group(1)}{html.escape(letters[next(count)])}{t.group(2)}', svg)
    out = re.sub(r'<svg class="stat-art"[\s\S]*?</svg>', month_art, out)
    if name in LEGAL:
        note = strings.get('x-legal-note')
        if note and not check_tokens(EXTRA['x-legal-note'][0], note):
            link = render(note, {0: (f'<a href="{url("en", slug)}" hreflang="en" data-lang="en">', '</a>')}, code=code)
            out = out.replace('<article class="doc">', f'<article class="doc">\n          <p class="doc-note">{link}</p>', 1)
    return out


def build_404(all_strings):
    p = SITE / '404.html'
    src = p.read_text(encoding='utf-8')
    table = {}
    for code, strings in all_strings.items():
        if code == 'en':
            continue
        entry = {}
        for key, name in (('x-404-title', 'title'), ('x-404-lead', 'lead'), ('x-404-home', 'home'),
                          ('x-404-support', 'support'), ('x-404-doc-title', 'doc-title')):
            t = strings.get(key)
            if t is None or check_tokens(EXTRA[key][0], t):
                continue
            # the title goes in as HTML (it carries the gradient span); the rest as text
            entry[name] = render(t, {0: ('<span class="grad-text">', '</span>')}) if key == 'x-404-title' else t
        entry['dir'] = BY_CODE[code][4]
        entry['lang'] = BY_CODE[code][1]
        table[code] = entry
    script = ('<!-- i18n:404 -->\n  <script>\n    (function () {\n'
              '      /* One 404 page serves every path: speak the language of the path, of the\n'
              '         menu choice, or of the browser. */\n'
              f'      var T = {json.dumps(table, ensure_ascii=False)};\n'
              '      var seg = location.pathname.split("/")[1] || "";\n'
              '      var saved = null; try { saved = localStorage.getItem("milesta-lang"); } catch (e) {}\n'
              '      var code = T[seg] ? seg : (T[saved] ? saved : null);\n'
              '      if (!code && saved !== "en") {\n'
              '        var list = navigator.languages && navigator.languages.length ? navigator.languages : [navigator.language || ""];\n'
              '        for (var i = 0; i < list.length && !code; i++) {\n'
              '          var p = String(list[i]).toLowerCase().split("-")[0];\n'
              '          if (p === "en") break;\n'
              '          var c = p === "zh" ? "zh-hans" : p === "pt" ? "pt-br" : p;\n'
              '          if (T[c]) code = c;\n'
              '        }\n'
              '      }\n'
              '      if (!code) return;\n'
              '      var t = T[code], d = document.documentElement;\n'
              '      d.lang = t.lang; d.dir = t.dir;\n'
              '      if (t["doc-title"]) document.title = t["doc-title"];\n'
              '      document.addEventListener("DOMContentLoaded", function () {\n'
              '        var q = function (s) { return document.querySelector(s); };\n'
              '        if (t.title) q(".doc-title").innerHTML = t.title;\n'
              '        if (t.lead) q(".doc-lead").textContent = t.lead;\n'
              '        var home = q(".doc-actions .btn-grad"), help = q(".doc-actions .btn-ghost");\n'
              '        if (t.home) { home.textContent = t.home; home.href = "/" + code; }\n'
              '        if (t.support) { help.textContent = t.support; help.href = "/" + code + "/support"; }\n'
              '      });\n'
              '    })();\n  </script>\n  <!-- /i18n:404 -->')
    src = replace_block(src, '404', script)
    p.write_text(src, encoding='utf-8')


def build_sitemap():
    rows = ['<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">']
    for name, slug in PAGES.items():
        for code, lang, *_ in LANGS:
            rows.append('  <url>')
            rows.append(f'    <loc>{ORIGIN}{url(code, slug)}</loc>')
            rows.append(f'    <priority>{"1.0" if not slug and code == "en" else "0.8" if not slug else "0.5"}</priority>')
            for c2, l2, *_ in LANGS:
                rows.append(f'    <xhtml:link rel="alternate" hreflang="{l2}" href="{ORIGIN}{url(c2, slug)}"/>')
            rows.append(f'    <xhtml:link rel="alternate" hreflang="x-default" href="{ORIGIN}{url("en", slug)}"/>')
            rows.append('  </url>')
    rows += ['  <url>', f'    <loc>{ORIGIN}/impressum</loc>', '    <priority>0.3</priority>', '  </url>', '</urlset>', '']
    (SITE / 'sitemap.xml').write_text('\n'.join(rows), encoding='utf-8')


# -------------------------------------------------------------- commands

def extract():
    seen = {}
    for name in PAGES:
        src = (SITE / name).read_text(encoding='utf-8')
        for u in collect_units(src, name):
            e = seen.setdefault(u.id, {'id': u.id, 'source': u.source, 'contexts': []})
            if u.context not in e['contexts']:
                e['contexts'].append(u.context)
    for key, (text, note) in EXTRA.items():
        seen[key] = {'id': key, 'source': text, 'contexts': [note]}
    units = list(seen.values())
    (I18N / 'source.json').write_text(json.dumps(units, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    words = sum(len(re.sub(r'</?\d+/?>', ' ', u['source']).split()) for u in units)
    print(f'{len(units)} strings, {words} words -> i18n/source.json')


def check():
    source = {u['id']: u['source'] for u in json.loads((I18N / 'source.json').read_text(encoding='utf-8'))}
    problems = 0
    for code, *_ in LANGS[1:]:
        strings = load_strings(code)
        if strings is None:
            print(f'{code}: no strings yet')
            continue
        missing = [k for k in source if k not in strings]
        stale = [k for k in strings if k not in source]
        bad = [(k, check_tokens(source[k], strings[k])) for k in source if k in strings and check_tokens(source[k], strings[k])]
        problems += len(missing) + len(bad)
        print(f'{code}: {len(strings)} strings, {len(missing)} missing, {len(stale)} stale, {len(bad)} malformed')
        for k, why in bad[:5]:
            print(f'    {k}: {why}')
    return problems


def build():
    errors = []
    all_strings = {'en': {}}
    for code, *_ in LANGS[1:]:
        s = load_strings(code)
        if s is not None:
            all_strings[code] = s
    # English pages: refresh the generated blocks in place.
    for name, slug in PAGES.items():
        p = SITE / name
        src = p.read_text(encoding='utf-8')
        src = replace_block(src, 'head', head_block('en', slug))
        src = replace_block(src, 'menu', menu_html('en', slug, {}))
        p.write_text(src, encoding='utf-8')
    # Impressum and 404 get the menu too (it leads to each language's home).
    for extra in ('impressum.html', '404.html'):
        p = SITE / extra
        src = p.read_text(encoding='utf-8')
        src = replace_block(src, 'menu', menu_html('en', '', {}))
        p.write_text(src, encoding='utf-8')
    for code, strings in all_strings.items():
        if code == 'en':
            continue
        (SITE / code).mkdir(exist_ok=True)
        for name, slug in PAGES.items():
            out = build_page(name, code, strings, errors)
            target = SITE / code / ('index.html' if not slug else f'{slug}.html')
            target.write_text(out, encoding='utf-8')
    build_404(all_strings)
    build_sitemap()
    for e in errors:
        print('ERROR', e)
    print(f'built {len(all_strings) - 1} languages, {len(errors)} errors')
    return len(errors)


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'build'
    sys.exit({'extract': extract, 'check': check, 'build': build}[cmd]() and 1 or 0)
