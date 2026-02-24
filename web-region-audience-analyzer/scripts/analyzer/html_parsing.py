"""
html_parsing.py — HTML text extraction utilities.
Provides BS4-based and stdlib-based parsers.
"""
import re
from html.parser import HTMLParser

try:
    from bs4 import BeautifulSoup, Comment
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False


class SimpleHTMLParser(HTMLParser):
    """Stdlib-only fallback when BeautifulSoup is not available."""
    def __init__(self):
        super().__init__()
        self.lang = None
        self.meta_tags = {}
        self.hreflangs = []
        self.text_parts = []
        self._skip = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'html':
            self.lang = a.get('lang')
        elif tag == 'meta':
            key = a.get('name') or a.get('property') or a.get('http-equiv')
            val = a.get('content')
            if key and val:
                self.meta_tags[key.lower()] = val
            if a.get('charset'):
                self.meta_tags['charset'] = a['charset']
        elif tag == 'link' and a.get('rel') == 'alternate' and a.get('hreflang'):
            self.hreflangs.append(a['hreflang'])
        elif tag in ('script', 'style', 'noscript'):
            self._skip = True

    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'noscript'):
            self._skip = False

    def handle_data(self, data):
        if not self._skip:
            t = data.strip()
            if t:
                self.text_parts.append(t)


def _extract_charset_from_content_type(meta_tags):
    """Parse charset from content-type meta http-equiv."""
    ct = meta_tags.get('content-type', '')
    m = re.search(r'charset=([^\s;]+)', ct, re.IGNORECASE)
    return m.group(1).strip() if m else None


def _extract_text_bs4(html):
    """Extract visible text using BeautifulSoup, handling CJK-heavy pages."""
    soup = BeautifulSoup(html, 'html.parser')

    for tag in soup.find_all(['script', 'style', 'noscript']):
        tag.decompose()
    for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
        comment.extract()

    html_tag = soup.find('html')
    lang = html_tag.get('lang') if html_tag else None

    meta_tags = {}
    for meta in soup.find_all('meta'):
        key = meta.get('name') or meta.get('property') or meta.get('http-equiv')
        val = meta.get('content')
        if key and val:
            meta_tags[key.lower()] = val
        if meta.get('charset'):
            meta_tags['charset'] = meta['charset']

    hreflangs = [
        link.get('hreflang')
        for link in soup.find_all('link', rel='alternate')
        if link.get('hreflang')
    ]

    title_tag = soup.find('title')
    title_text = title_tag.get_text(strip=True) if title_tag else ''

    body = soup.find('body')
    if body:
        body_text = body.get_text(separator=' ', strip=True)
    else:
        body_text = soup.get_text(separator=' ', strip=True)

    text_content = (title_text + ' ' + body_text).strip()

    desc = meta_tags.get('description', '')
    keywords = meta_tags.get('keywords', '')
    if len(text_content) < 50:
        text_content = ' '.join(filter(None, [text_content, desc, keywords])).strip()

    return lang, meta_tags, hreflangs, text_content


def _extract_text_stdlib(html):
    """Fallback text extraction using stdlib HTMLParser."""
    parser = SimpleHTMLParser()
    parser.feed(html)
    text_content = ' '.join(parser.text_parts)

    desc = parser.meta_tags.get('description', '')
    keywords = parser.meta_tags.get('keywords', '')
    if len(text_content) < 50:
        text_content = ' '.join(filter(None, [text_content, desc, keywords])).strip()

    return parser.lang, parser.meta_tags, parser.hreflangs, text_content
