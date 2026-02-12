#!/usr/bin/env python3
"""
Web Region & Audience Analyzer
Analyzes a web page to infer its geographic region, target audience, and primary language
by fusing multiple signal sources: HTML metadata, content patterns, IP geolocation,
and language detection.
"""
import argparse
import json
import os
import re
import socket
import ssl
import sys
import time
import urllib.request
import urllib.parse
from collections import deque
from datetime import datetime, timezone
from html.parser import HTMLParser

try:
    from export_utils import build_default_markdown_output_path
except ImportError:
    build_default_markdown_output_path = None

# Optional dependencies
try:
    from bs4 import BeautifulSoup, Comment
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

try:
    from langdetect import detect_langs, DetectorFactory
    DetectorFactory.seed = 0
    HAS_LANGDETECT = True
except ImportError:
    HAS_LANGDETECT = False

# ============================================================================
# Constants & Mappings
# ============================================================================

TLD_MAP = {
    '.cn': 'CN', '.de': 'DE', '.jp': 'JP', '.uk': 'GB', '.fr': 'FR', '.ru': 'RU',
    '.br': 'BR', '.in': 'IN', '.kr': 'KR', '.au': 'AU', '.ca': 'CA', '.it': 'IT',
    '.es': 'ES', '.nl': 'NL', '.se': 'SE', '.no': 'NO', '.dk': 'DK', '.fi': 'FI',
    '.pl': 'PL', '.tr': 'TR', '.id': 'ID', '.vn': 'VN', '.th': 'TH', '.my': 'MY',
    '.sg': 'SG', '.ph': 'PH', '.mx': 'MX', '.ar': 'AR', '.cl': 'CL', '.co': 'CO',
    '.za': 'ZA', '.eg': 'EG', '.sa': 'SA', '.ae': 'AE', '.il': 'IL', '.nz': 'NZ',
    '.ie': 'IE', '.ch': 'CH', '.at': 'AT', '.be': 'BE', '.pt': 'PT', '.gr': 'GR',
    '.cz': 'CZ', '.hu': 'HU', '.ro': 'RO', '.ua': 'UA', '.tw': 'TW', '.hk': 'HK',
}

# FIX #1: Map bare language codes to primary country codes
LANG_TO_REGION = {
    'zh': 'CN', 'ja': 'JP', 'ko': 'KR', 'de': 'DE', 'fr': 'FR', 'ru': 'RU',
    'pt': 'BR', 'it': 'IT', 'es': 'ES', 'nl': 'NL', 'pl': 'PL', 'tr': 'TR',
    'vi': 'VN', 'th': 'TH', 'id': 'ID', 'ms': 'MY', 'tl': 'PH', 'ar': 'SA',
    'he': 'IL', 'hi': 'IN', 'bn': 'BD', 'uk': 'UA', 'cs': 'CZ', 'hu': 'HU',
    'ro': 'RO', 'el': 'GR', 'sv': 'SE', 'no': 'NO', 'da': 'DK', 'fi': 'FI',
    'fa': 'IR', 'sw': 'KE',
    # English intentionally excluded -- too global to map to one country
}

# FIX #9: Country code to human-readable name
COUNTRY_NAMES = {
    'CN': 'China', 'US': 'United States', 'DE': 'Germany', 'JP': 'Japan',
    'GB': 'United Kingdom', 'FR': 'France', 'RU': 'Russia', 'BR': 'Brazil',
    'IN': 'India', 'KR': 'South Korea', 'AU': 'Australia', 'CA': 'Canada',
    'IT': 'Italy', 'ES': 'Spain', 'NL': 'Netherlands', 'SE': 'Sweden',
    'NO': 'Norway', 'DK': 'Denmark', 'FI': 'Finland', 'PL': 'Poland',
    'TR': 'Turkey', 'ID': 'Indonesia', 'VN': 'Vietnam', 'TH': 'Thailand',
    'MY': 'Malaysia', 'SG': 'Singapore', 'PH': 'Philippines', 'MX': 'Mexico',
    'AR': 'Argentina', 'CL': 'Chile', 'CO': 'Colombia', 'ZA': 'South Africa',
    'EG': 'Egypt', 'SA': 'Saudi Arabia', 'AE': 'UAE', 'IL': 'Israel',
    'NZ': 'New Zealand', 'IE': 'Ireland', 'CH': 'Switzerland', 'AT': 'Austria',
    'BE': 'Belgium', 'PT': 'Portugal', 'GR': 'Greece', 'CZ': 'Czech Republic',
    'HU': 'Hungary', 'RO': 'Romania', 'UA': 'Ukraine', 'TW': 'Taiwan',
    'HK': 'Hong Kong', 'BD': 'Bangladesh', 'IR': 'Iran', 'KE': 'Kenya',
    'EU': 'European Union',
}

LANG_NAMES = {
    'en': 'English', 'zh': 'Chinese', 'zh-cn': 'Simplified Chinese',
    'zh-tw': 'Traditional Chinese', 'ja': 'Japanese', 'ko': 'Korean',
    'de': 'German', 'fr': 'French', 'es': 'Spanish', 'pt': 'Portuguese',
    'ru': 'Russian', 'ar': 'Arabic', 'hi': 'Hindi', 'it': 'Italian',
    'nl': 'Dutch', 'pl': 'Polish', 'tr': 'Turkish', 'vi': 'Vietnamese',
    'th': 'Thai', 'id': 'Indonesian', 'ms': 'Malay', 'sv': 'Swedish',
    'no': 'Norwegian', 'da': 'Danish', 'fi': 'Finnish', 'he': 'Hebrew',
    'uk': 'Ukrainian', 'cs': 'Czech', 'hu': 'Hungarian', 'ro': 'Romanian',
    'el': 'Greek', 'fa': 'Persian', 'bn': 'Bengali', 'tl': 'Filipino',
}

PHONE_PREFIXES = {
    r'\+1(?=[\s\-\.(])': 'US', r'\+44': 'GB', r'\+86': 'CN', r'\+81': 'JP',
    r'\+49': 'DE', r'\+33': 'FR', r'\+7(?=[\s\-\.(])': 'RU', r'\+55': 'BR',
    r'\+91': 'IN', r'\+82': 'KR', r'\+61': 'AU', r'\+39': 'IT', r'\+34': 'ES',
    r'\+31': 'NL', r'\+46': 'SE', r'\+47': 'NO', r'\+45': 'DK', r'\+358': 'FI',
    r'\+48': 'PL', r'\+90': 'TR', r'\+62': 'ID', r'\+84': 'VN', r'\+66': 'TH',
    r'\+60': 'MY', r'\+65': 'SG', r'\+63': 'PH', r'\+52': 'MX', r'\+54': 'AR',
    r'\+56': 'CL', r'\+57': 'CO', r'\+27': 'ZA', r'\+20': 'EG', r'\+966': 'SA',
    r'\+971': 'AE', r'\+972': 'IL',
}

CURRENCY_MAP = {
    'USD': 'US', 'EUR': 'EU', 'CNY': 'CN', 'RMB': 'CN', 'GBP': 'GB', 'JPY': 'JP',
    'INR': 'IN', 'RUB': 'RU', 'BRL': 'BR', 'KRW': 'KR', 'AUD': 'AU', 'CAD': 'CA',
    'CHF': 'CH', 'HKD': 'HK', 'SGD': 'SG', 'SEK': 'SE', 'NOK': 'NO', 'DKK': 'DK',
    'PLN': 'PL', 'TRY': 'TR', 'THB': 'TH', 'IDR': 'ID', 'MYR': 'MY', 'PHP': 'PH',
    'VND': 'VN', 'MXN': 'MX', 'ZAR': 'ZA', 'ILS': 'IL', 'SAR': 'SA', 'AED': 'AE',
}

# FIX #5: Ordered patterns with word boundaries to prevent false positives
CURRENCY_SYMBOLS = [
    (r'R\$', 'BRL'), (r'HK\$', 'HKD'), (r'S\$', 'SGD'), (r'Mex\$', 'MXN'),
    (r'(?<![A-Za-z])\$', 'USD'), (r'€', 'EUR'), (r'£', 'GBP'), (r'¥', 'CNY/JPY'),
    (r'₹', 'INR'), (r'₽', 'RUB'), (r'₩', 'KRW'), (r'zł', 'PLN'), (r'₺', 'TRY'),
    (r'฿', 'THB'), (r'₱', 'PHP'), (r'₫', 'VND'),
    (r'(?<!\w)Rp(?:\s|\.)', 'IDR'), (r'(?<!\w)RM(?:\s|\.|\d)', 'MYR'),
    (r'(?<![A-Za-z])kr(?:\s|\.|,|\d)', 'SEK/NOK/DKK'),
]

SOCIAL_MEDIA_DOMAINS = {
    'weixin.qq.com': 'CN', 'weibo.com': 'CN', 'douyin.com': 'CN',
    'bilibili.com': 'CN', 'zhihu.com': 'CN', 'baidu.com': 'CN',
    'vk.com': 'RU', 'ok.ru': 'RU', 'mail.ru': 'RU',
    'line.me': 'JP', 'nicovideo.jp': 'JP', 'ameblo.jp': 'JP',
    'kakaotalk.com': 'KR', 'naver.com': 'KR', 'daum.net': 'KR',
}

# Payment methods expected in specific regions
PAYMENT_METHODS = {
    'NL': ['iDEAL'],
    'DE': ['Sofort', 'Giropay', 'Klarna', 'SEPA', 'Rechnung'],
    'AT': ['EPS'],
    'PL': ['BLIK', 'Przelewy24'],
    'BR': ['Pix', 'Boleto'],
    'BE': ['Bancontact'],
    'CN': ['Alipay', 'WeChat Pay', 'UnionPay'],
    'JP': ['Konbini', 'JCB', 'PayPay'],
    'RU': ['Mir', 'Yandex'],
    'IN': ['UPI', 'RuPay', 'Paytm'],
    'SE': ['Swish'],
    'CH': ['TWINT'],
}

# Spelling variants (US vs UK)
SPELLING_VARIANTS = {
    'US': [r'\bcolor\b', r'\bflavor\b', r'\bcenter\b', r'\bmeter\b', r'\blicense\b', r'\bshipping\b'],
    'UK': [r'\bcolour\b', r'\bflavour\b', r'\bcentre\b', r'\bmetre\b', r'\blicence\b', r'\bdelivery\b'],
}

# Measurement units
MEASUREMENT_UNITS = {
    'Imperial': [r'\binch(?:es)?\b', r'\blbs?\b', r'\boz\b', r'\bfeet\b', r'\byards?\b'],
    'Metric': [r'\bcm\b', r'\bkg\b', r'\bml\b', r'\bmeters?\b', r'\bliters?\b'],
}

# ============================================================================
# HTML Parsing
# ============================================================================

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
    """FIX #6: Parse charset from content-type meta http-equiv."""
    ct = meta_tags.get('content-type', '')
    m = re.search(r'charset=([^\s;]+)', ct, re.IGNORECASE)
    return m.group(1).strip() if m else None


def _extract_text_bs4(html):
    """Extract visible text using BeautifulSoup, handling CJK-heavy pages."""
    soup = BeautifulSoup(html, 'html.parser')

    # Remove script/style/comment nodes
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

    # FIX #4: Get text from title + body separately to handle minimal pages
    title_tag = soup.find('title')
    title_text = title_tag.get_text(strip=True) if title_tag else ''

    body = soup.find('body')
    if body:
        body_text = body.get_text(separator=' ', strip=True)
    else:
        body_text = soup.get_text(separator=' ', strip=True)

    text_content = (title_text + ' ' + body_text).strip()

    # Also try meta description / keywords as fallback text
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

# ============================================================================
# Core Functions
# ============================================================================

def fetch_html(url, timeout=15):
    """FIX #8: Try multiple SSL strategies for resilient fetching."""
    headers = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }

    strategies = [
        lambda: ssl.create_default_context(),
        lambda: _permissive_ssl_context(),
    ]

    last_error = None
    for make_ctx in strategies:
        try:
            ctx = make_ctx()
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                raw = resp.read()
                charset = 'utf-8'
                ct = resp.headers.get('Content-Type', '')
                m = re.search(r'charset=([^\s;]+)', ct, re.IGNORECASE)
                if m:
                    charset = m.group(1)
                try:
                    html = raw.decode(charset, errors='replace')
                except (LookupError, UnicodeDecodeError):
                    html = raw.decode('utf-8', errors='replace')
                return html, resp.geturl(), None
        except Exception as e:
            last_error = e
            continue

    return None, None, str(last_error)


def _permissive_ssl_context():
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        ctx.set_ciphers('DEFAULT:@SECLEVEL=1')
    except ssl.SSLError:
        ctx.set_ciphers('DEFAULT')
    return ctx


def _extract_ux_signals(html):
    """Extract UX-related signals: viewport, inputs, images, preconnects."""
    signals = {
        'viewport': None,
        'inputs': [],
        'images': [],
        'links': [],
    }

    if HAS_BS4:
        soup = BeautifulSoup(html, 'html.parser')

        # Viewport
        vp = soup.find('meta', attrs={'name': 'viewport'})
        if vp:
            signals['viewport'] = vp.get('content')

        # Inputs
        for inp in soup.find_all('input'):
            signals['inputs'].append({
                'type': inp.get('type'),
                'inputmode': inp.get('inputmode'),
                'autocomplete': inp.get('autocomplete'),
                'name': inp.get('name'),
            })

        # Images (sample first 20 to avoid huge payload)
        for img in soup.find_all('img', limit=20):
            signals['images'].append({
                'alt': img.get('alt'),
                'loading': img.get('loading'),
                'width': img.get('width'),
                'height': img.get('height'),
            })

        # Links (preconnect)
        for link in soup.find_all('link'):
            rel = link.get('rel')
            if rel and ('preconnect' in rel or 'dns-prefetch' in rel):
                signals['links'].append({
                    'rel': rel,
                    'href': link.get('href'),
                })

    else:
        # Regex fallback
        vp_match = re.search(r'<meta[^>]+name=["\']viewport["\'][^>]+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
        if vp_match:
            signals['viewport'] = vp_match.group(1)

        # Simple input scan
        for m in re.finditer(r'<input([^>]+)>', html, re.IGNORECASE):
            attrs = m.group(1)
            type_m = re.search(r'type=["\']([^"\']+)["\']', attrs)
            mode_m = re.search(r'inputmode=["\']([^"\']+)["\']', attrs)
            auto_m = re.search(r'autocomplete=["\']([^"\']+)["\']', attrs)
            signals['inputs'].append({
                'type': type_m.group(1) if type_m else None,
                'inputmode': mode_m.group(1) if mode_m else None,
                'autocomplete': auto_m.group(1) if auto_m else None,
            })

        # Simple img scan (limit 20)
        count = 0
        for m in re.finditer(r'<img([^>]+)>', html, re.IGNORECASE):
            if count >= 20: break
            attrs = m.group(1)
            alt_m = re.search(r'alt=["\']([^"\']*)["\']', attrs)
            load_m = re.search(r'loading=["\']([^"\']+)["\']', attrs)
            signals['images'].append({
                'alt': alt_m.group(1) if alt_m else None,
                'loading': load_m.group(1) if load_m else None,
            })
            count += 1

    return signals


def extract_persona_enhanced_signals(html, text_content, persona_focus):
    """Extract persona-focused enhanced signals based on focus areas.
    
    Args:
        html: HTML content
        text_content: Extracted text content
        persona_focus: Dictionary of focus areas (price_sensitive, mobile_first, local_trust)
    
    Returns:
        Dictionary of enhanced signals
    """
    enhanced = {}
    
    # Price-sensitive signals
    if persona_focus.get('price_sensitive'):
        # Detect pricing structure
        price_patterns = [
            (r'price[-_]?display|original[-_]?price|list[-_]?price', 'pricing_display'),
            (r'\$\d+\.?\d*', 'price_format'),
            (r'was|was[: ]+\$|from[: ]+\$|regular[- ]?price', 'original_price'),
            (r'sale|discount|off|save|-\d+%|\d+[%] off', 'discount_display'),
            (r'best[- ]?price|lowest[- ]?price', 'price_comparison'),
            (r'\$\d+\.?\d*\s*USD|\$\d+\.?\d*\s*CAD', 'currency_display'),
        ]
        
        pricing_info = {}
        for pattern, key in price_patterns:
            if re.search(pattern, html, re.IGNORECASE):
                pricing_info[key] = True
            else:
                pricing_info[key] = False
        
        enhanced['pricing'] = pricing_info
        
        # Check for value proposition
        value_keywords = ['value', 'save', 'deal', 'bundle', 'pack', 'combo', 'best value']
        enhanced['value_proposition'] = any(kw in text_content.lower() for kw in value_keywords)
    
    # Mobile-first signals
    if persona_focus.get('mobile_first'):
        # Check viewport
        viewport = re.search(r'<meta[^>]*name=["\']viewport["\']([^"\']*)', html, re.IGNORECASE)
        enhanced['viewport_configured'] = bool(viewport)
        
        if viewport:
            vp_content = viewport.group(1).lower()
            enhanced['viewport_mobile_optimized'] = all([
                'width=device-width' in vp_content,
                'initial-scale=1' in vp_content,
            ])
        
        # Check for touch-optimized elements
        enhanced['has_touch_elements'] = bool(re.search(
            r'(<button|<a[^>]*href)', html, re.IGNORECASE
        ))
        
        # Check for mobile-specific CSS classes
        mobile_classes = ['mobile-', 'touch-', 'responsive-', 'xs-', 'sm-']
        enhanced['has_mobile_classes'] = any(
            cls in html for cls in mobile_classes
        )
    
    # Local trust signals
    if persona_focus.get('local_trust'):
        # Check for local reviews
        enhanced['has_local_reviews'] = bool(re.search(
            r'review|rating|testimonial|star|verified|badge', 
            html, re.IGNORECASE
        ))
        
        # Check for trust signals
        trust_signals = [
            (r'secure|ssl|https|locked|shield', 'security_badges'),
            (r'guarantee|warranty|refund|policy', 'guarantee_display'),
            (r'certified|accredited|verified|trusted', 'trust_badges'),
            (r'shipping|delivery|fulfillment', 'shipping_info'),
        ]
        
        trust_info = {}
        for pattern, key in trust_signals:
            trust_info[key] = bool(re.search(pattern, html, re.IGNORECASE))
        
        enhanced['trust_signals'] = trust_info
        
        # Check for local-specific content
        local_keywords = ['canadian', 'canada', 'local', 'domestic']
        enhanced['has_local_content'] = any(
            kw in text_content.lower() for kw in local_keywords
        )
    
    return enhanced


def extract_signals(html, url):
    """Extract all signals from HTML content."""
    if HAS_BS4:
        lang, meta_tags, hreflangs, text_content = _extract_text_bs4(html)
    else:
        lang, meta_tags, hreflangs, text_content = _extract_text_stdlib(html)

    # FIX #6: charset from content-type header
    charset = meta_tags.get('charset') or _extract_charset_from_content_type(meta_tags)

    html_signals = {
        'lang': lang,
        'metaLocale': meta_tags.get('og:locale'),
        'metaLanguage': meta_tags.get('content-language'),
        'metaGeoRegion': meta_tags.get('geo.region'),
        'metaGeoPlacename': meta_tags.get('geo.placename'),
        'charset': charset,
        'hreflangTags': hreflangs,
    }

    # TLD -- handle compound TLDs like .co.jp, .co.uk
    parsed = urllib.parse.urlparse(url)
    domain = parsed.netloc.lower().lstrip('www.')
    parts = domain.split('.')
    tld = None
    if len(parts) >= 2:
        simple_tld = '.' + parts[-1]
        compound_tld = '.' + '.'.join(parts[-2:])
        if compound_tld in ('.co.jp', '.co.uk', '.co.kr', '.co.in', '.co.nz',
                            '.co.za', '.co.th', '.co.id'):
            tld = '.' + parts[-1]
        elif simple_tld in TLD_MAP:
            tld = simple_tld
    html_signals['tld'] = tld if tld and tld in TLD_MAP else None

    # Content Signals
    currency_codes = [
        code for code in CURRENCY_MAP
        if re.search(r'\b' + code + r'\b', text_content)
    ]
    # FIX #5: ordered symbol patterns with word-boundary-safe regexes
    currency_symbols = []
    for pattern, sym in CURRENCY_SYMBOLS:
        if re.search(pattern, text_content):
            currency_symbols.append(sym)

    phone_formats = [
        country for pattern, country in PHONE_PREFIXES.items()
        if re.search(pattern, text_content)
    ]

    social_signals = [
        {'domain': dom, 'region': region}
        for dom, region in SOCIAL_MEDIA_DOMAINS.items()
        if dom in html
    ]

    # NEW: Payment Methods
    payment_methods = []
    for region, methods in PAYMENT_METHODS.items():
        for method in methods:
            if re.search(r'\b' + re.escape(method) + r'\b', text_content, re.IGNORECASE):
                payment_methods.append({'method': method, 'region': region})

    # NEW: Spelling Check
    spelling_counts = {'US': 0, 'UK': 0}
    for variant, patterns in SPELLING_VARIANTS.items():
        for pattern in patterns:
            if re.search(pattern, text_content, re.IGNORECASE):
                spelling_counts[variant] += 1

    # NEW: Measurement Units
    unit_counts = {'Imperial': 0, 'Metric': 0}
    for system, patterns in MEASUREMENT_UNITS.items():
        for pattern in patterns:
            if re.search(pattern, text_content, re.IGNORECASE):
                unit_counts[system] += 1

    # NEW: UX Signals
    ux_signals = _extract_ux_signals(html)

    content_signals = {
        'currencyCodes': currency_codes,
        'currencySymbols': list(dict.fromkeys(currency_symbols)),
        'phoneFormats': phone_formats,
        'socialMediaSignals': social_signals,
        'paymentMethods': payment_methods,
        'spellingCounts': spelling_counts,
        'unitCounts': unit_counts,
        'uxSignals': ux_signals,
        'enhanced': {},  # Placeholder for persona-driven enhancements
    }

    return {'htmlSignals': html_signals, 'contentSignals': content_signals}, text_content


def get_ip_geo(domain):
    """Resolve domain IP and query ip-api.com for geolocation."""
    try:
        ip = socket.gethostbyname(domain)
    except socket.gaierror as e:
        return {'error': f'DNS resolution failed: {e}'}

    api_url = (
        f"http://ip-api.com/json/{ip}"
        f"?fields=status,message,country,countryCode,region,regionName,"
        f"city,zip,lat,lon,timezone,isp,org,as,query"
    )
    try:
        with urllib.request.urlopen(api_url, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            if data.get('status') == 'success':
                return data
            return {'error': data.get('message', 'Unknown error')}
    except Exception as e:
        return {'error': str(e)}


def detect_language_nlpcloud(text, token):
    api_url = "https://api.nlpcloud.io/v1/gpu/lang-detect"
    headers = {
        "Authorization": f"Token {token}",
        "Content-Type": "application/json",
    }
    body = json.dumps({"text": text[:5000]}).encode('utf-8')
    req = urllib.request.Request(api_url, data=body, headers=headers, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        return {'error': str(e)}


def detect_language_offline(text):
    if not HAS_LANGDETECT:
        return {'error': 'langdetect not installed (pip install langdetect)'}
    if not text or len(text.strip()) < 10:
        return {'error': 'Insufficient text for language detection'}
    try:
        langs = detect_langs(text[:5000])
        return {'results': [{'lang': str(l.lang), 'confidence': round(l.prob, 6)} for l in langs]}
    except Exception as e:
        return {'error': str(e)}


# ============================================================================
# Signal Fusion & Scoring
# ============================================================================

def compute_result(evidence):
    """
    FIX #2, #3: Proper multi-signal fusion with weighted scoring.

    Signal weights:
      TLD              1.0   (strong, explicit)
      html lang region 0.9   (explicit declaration with region subtag)
      html lang->region 0.7  (inferred from bare lang code)
      langdetect       0.6   (statistical, contributes via LANG_TO_REGION)
      og:locale region 0.8   (explicit)
      content-language 0.7   (explicit meta)
      IP geolocation   0.4   (can be CDN/proxy -- weaker)
      currency codes   0.3   (per unique match)
      phone prefixes   0.3   (per unique match)
      social media     0.3   (per unique match)
    """
    scores = {}
    max_weight = 0.0
    primary_lang = None
    lang_confidence = 0.0

    html_s = evidence.get('htmlSignals', {})
    content_s = evidence.get('contentSignals', {})
    ip_geo = evidence.get('ipGeolocation', {})
    lang_det = evidence.get('languageDetection', {})

    def add_score(region, weight):
        nonlocal max_weight
        if region:
            scores[region] = scores.get(region, 0) + weight
            max_weight += weight

    # --- TLD ---
    tld = html_s.get('tld')
    if tld and tld in TLD_MAP:
        add_score(TLD_MAP[tld], 1.0)
    else:
        max_weight += 1.0

    # --- HTML lang attribute ---
    lang = html_s.get('lang')
    if lang:
        lang_lower = lang.lower().strip()
        parts = re.split(r'[-_]', lang_lower)
        lang_code = parts[0]

        if len(parts) >= 2:
            region = parts[1].upper()
            add_score(region, 0.9)
            primary_lang = lang_lower
        elif lang_code in LANG_TO_REGION:
            # FIX #1: Infer region from bare lang code
            add_score(LANG_TO_REGION[lang_code], 0.7)
            primary_lang = lang_code
        else:
            primary_lang = lang_code
            max_weight += 0.7
    else:
        max_weight += 0.9

    # --- og:locale ---
    locale = html_s.get('metaLocale')
    if locale:
        parts = locale.split('_')
        if len(parts) >= 2:
            add_score(parts[1].upper(), 0.8)
        elif parts[0].lower() in LANG_TO_REGION:
            add_score(LANG_TO_REGION[parts[0].lower()], 0.5)
    else:
        max_weight += 0.8

    # --- content-language meta ---
    content_lang = html_s.get('metaLanguage')
    if content_lang:
        cl_parts = re.split(r'[-_]', content_lang.lower().strip())
        if len(cl_parts) >= 2:
            add_score(cl_parts[1].upper(), 0.7)
        elif cl_parts[0] in LANG_TO_REGION:
            add_score(LANG_TO_REGION[cl_parts[0]], 0.5)
    else:
        max_weight += 0.7

    # --- FIX #2: Language detection results contribute to scoring ---
    if 'results' in lang_det and lang_det['results']:
        top = lang_det['results'][0]
        detected_lang = top['lang']
        detected_conf = top.get('confidence', 0)

        if not primary_lang:
            primary_lang = detected_lang
        lang_confidence = detected_conf

        if detected_lang in LANG_TO_REGION and detected_conf > 0.5:
            add_score(LANG_TO_REGION[detected_lang], 0.6 * detected_conf)
        else:
            max_weight += 0.6
    else:
        max_weight += 0.6

    # --- IP Geolocation ---
    if 'countryCode' in ip_geo:
        isp = (ip_geo.get('isp', '') + ' ' + ip_geo.get('org', '')).lower()
        is_cdn = any(cdn in isp for cdn in [
            'cloudflare', 'akamai', 'fastly', 'cloudfront', 'twitter',
            'edgecast', 'stackpath', 'incapsula', 'sucuri',
        ])
        ip_weight = 0.2 if is_cdn else 0.4
        add_score(ip_geo['countryCode'], ip_weight)
    else:
        max_weight += 0.4

    # --- Currency codes ---
    for code in content_s.get('currencyCodes', []):
        if code in CURRENCY_MAP:
            add_score(CURRENCY_MAP[code], 0.3)

    # --- Phone prefixes ---
    for country in content_s.get('phoneFormats', []):
        add_score(country, 0.3)

    # --- Social media ---
    for sig in content_s.get('socialMediaSignals', []):
        region = sig.get('region', '')
        if '/' not in region:
            add_score(region, 0.3)

    # --- Determine primary region ---
    if scores:
        primary_region = max(scores, key=lambda k: scores[k])
        # FIX #3: Better normalization
        raw_conf = scores[primary_region]
        if max_weight > 0:
            confidence = min(raw_conf / max_weight, 1.0)
        else:
            confidence = min(raw_conf, 1.0)
        confidence = round(confidence, 2)
    else:
        primary_region = None
        confidence = 0.0

    if not primary_lang and primary_region:
        for lc, rc in LANG_TO_REGION.items():
            if rc == primary_region:
                primary_lang = lc
                break

    # FIX #7 & #9: Rich audience description
    country_name = COUNTRY_NAMES.get(primary_region, primary_region) if primary_region else None
    lang_name = LANG_NAMES.get(primary_lang, primary_lang) if primary_lang else None

    if primary_region and primary_lang:
        audience = f"{lang_name}-speaking audience in {country_name}"
    elif primary_region:
        audience = f"Audience in {country_name}"
    else:
        audience = "Unknown"

    return {
        'primaryRegion': primary_region,
        'primaryRegionName': country_name,
        'primaryLanguage': primary_lang,
        'primaryLanguageName': lang_name,
        'likelyAudience': audience,
        'regionConfidence': confidence,
        'languageConfidence': round(lang_confidence, 4) if lang_confidence else None,
        'signalBreakdown': {
            k: round(v, 3)
            for k, v in sorted(scores.items(), key=lambda x: -x[1])
        },
    }


# ============================================================================
# Cross-Border Optimization Recommendations
# ============================================================================

# Major markets that well-configured cross-border sites typically cover
MAJOR_MARKETS = ['en', 'zh', 'ja', 'ko', 'de', 'fr', 'es', 'pt', 'ru', 'ar']

# Region-to-currency: expected local currency for a target market
REGION_CURRENCY = {
    'US': ['USD'], 'GB': ['GBP'], 'EU': ['EUR'], 'DE': ['EUR'], 'FR': ['EUR'],
    'IT': ['EUR'], 'ES': ['EUR'], 'NL': ['EUR'], 'BE': ['EUR'], 'AT': ['EUR'],
    'PT': ['EUR'], 'GR': ['EUR'], 'FI': ['EUR'], 'IE': ['EUR'],
    'JP': ['JPY'], 'CN': ['CNY', 'RMB'], 'KR': ['KRW'], 'IN': ['INR'],
    'BR': ['BRL'], 'RU': ['RUB'], 'AU': ['AUD'], 'CA': ['CAD'],
    'MX': ['MXN'], 'TH': ['THB'], 'VN': ['VND'], 'ID': ['IDR'],
    'MY': ['MYR'], 'PH': ['PHP'], 'SG': ['SGD'], 'HK': ['HKD'],
    'SE': ['SEK'], 'NO': ['NOK'], 'DK': ['DKK'], 'PL': ['PLN'],
    'TR': ['TRY'], 'CH': ['CHF'], 'ZA': ['ZAR'], 'SA': ['SAR'],
    'AE': ['AED'], 'IL': ['ILS'], 'TW': ['TWD'],
}

# Region-to-social: expected regional social platforms
REGION_SOCIAL = {
    'CN': ['weixin.qq.com', 'weibo.com', 'douyin.com'],
    'RU': ['vk.com', 'ok.ru'],
    'JP': ['line.me'],
    'KR': ['kakaotalk.com', 'naver.com'],
}


def generate_recommendations(evidence, result):
    """
    Generate cross-border localization optimization recommendations.

    Analyzes signals for issues common in multilingual/cross-border websites:
    hreflang configuration, locale consistency, market adaptation, etc.

    Returns a list of recommendation dicts, each with:
      - severity: 'critical' | 'warning' | 'info'
      - category: short category label
      - issue: what's wrong
      - recommendation: what to do
      - codeExample: optional HTML/code snippet showing the fix
    """
    recs = []
    html_s = evidence.get('htmlSignals', {})
    content_s = evidence.get('contentSignals', {})
    ip_geo = evidence.get('ipGeolocation', {})
    lang_det = evidence.get('languageDetection', {})

    primary_region = result.get('primaryRegion')
    primary_lang = result.get('primaryLanguage')
    hreflangs = html_s.get('hreflangTags', [])
    lang_attr = html_s.get('lang')
    og_locale = html_s.get('metaLocale')
    content_language = html_s.get('metaLanguage')
    charset = html_s.get('charset')
    tld = html_s.get('tld')

    # ── 1. hreflang Audit ───────────────────────────────────────────────
    if not hreflangs:
        recs.append({
            'severity': 'critical',
            'category': 'hreflang',
            'issue': 'No hreflang tags found. Search engines cannot identify alternate language/region versions of this page.',
            'recommendation': (
                'Add <link rel="alternate" hreflang="..."> tags for every language/region '
                'variant of the page. This is essential for cross-border SEO to prevent '
                'duplicate content penalties and ensure correct regional versions appear in search results.'
            ),
            'codeExample': (
                '<link rel="alternate" hreflang="en" href="https://example.com/en/" />\n'
                '<link rel="alternate" hreflang="de" href="https://example.com/de/" />\n'
                '<link rel="alternate" hreflang="ja" href="https://example.com/ja/" />\n'
                '<link rel="alternate" hreflang="x-default" href="https://example.com/" />'
            ),
        })
    else:
        hreflang_lower = [h.lower() for h in hreflangs]

        # Missing x-default
        if 'x-default' not in hreflang_lower:
            recs.append({
                'severity': 'critical',
                'category': 'hreflang',
                'issue': 'hreflang tags exist but "x-default" is missing. Users from unmatched regions will not be routed to a fallback page.',
                'recommendation': (
                    'Add an x-default hreflang tag pointing to your default/fallback page '
                    '(usually English or a language selector page). This tells search engines '
                    'which URL to show for regions not explicitly covered by other hreflang tags.'
                ),
                'codeExample': '<link rel="alternate" hreflang="x-default" href="https://example.com/" />',
            })

        # Check self-referencing: current page's lang should be in hreflang list
        if primary_lang:
            primary_base = primary_lang.split('-')[0].split('_')[0]
            has_self_ref = any(
                h.split('-')[0].split('_')[0] == primary_base
                for h in hreflang_lower if h != 'x-default'
            )
            if not has_self_ref:
                recs.append({
                    'severity': 'warning',
                    'category': 'hreflang',
                    'issue': (
                        f'Current page language "{primary_lang}" does not have a matching '
                        f'self-referencing hreflang tag. Found hreflangs: {hreflangs}'
                    ),
                    'recommendation': (
                        'Each page should include a self-referencing hreflang tag for its own '
                        'language/region. This confirms to search engines which version this page represents.'
                    ),
                    'codeExample': f'<link rel="alternate" hreflang="{primary_lang}" href="[this page URL]" />',
                })

    # ── 2. Missing Locale Declarations ──────────────────────────────────
    if not lang_attr:
        recs.append({
            'severity': 'critical',
            'category': 'locale-declaration',
            'issue': 'Missing <html lang="..."> attribute. Browsers and screen readers cannot determine the page language.',
            'recommendation': (
                'Add a lang attribute to the <html> tag. For cross-border sites, this should '
                'reflect the language of the current page variant.'
            ),
            'codeExample': '<html lang="en">  <!-- or "de", "ja", "zh-CN", etc. -->',
        })

    if not og_locale:
        recs.append({
            'severity': 'warning',
            'category': 'locale-declaration',
            'issue': 'Missing og:locale meta tag. Social media platforms cannot determine content locale for sharing.',
            'recommendation': (
                'Add og:locale for correct social media card rendering. For multilingual sites, '
                'also add og:locale:alternate for other available locales.'
            ),
            'codeExample': (
                '<meta property="og:locale" content="en_US" />\n'
                '<meta property="og:locale:alternate" content="de_DE" />\n'
                '<meta property="og:locale:alternate" content="ja_JP" />'
            ),
        })

    if not content_language:
        recs.append({
            'severity': 'info',
            'category': 'locale-declaration',
            'issue': 'No content-language meta tag found. While less critical than <html lang>, it provides an additional signal.',
            'recommendation': (
                'Consider adding a content-language meta tag, especially if your HTTP server '
                'does not send a Content-Language header.'
            ),
            'codeExample': '<meta http-equiv="content-language" content="en" />',
        })

    # ── 3. Locale Signal Consistency ────────────────────────────────────
    # Compare lang attr vs og:locale vs content-language for conflicts
    declared_langs = {}
    if lang_attr:
        declared_langs['html lang'] = lang_attr.lower().split('-')[0].split('_')[0]
    if og_locale:
        declared_langs['og:locale'] = og_locale.lower().split('_')[0].split('-')[0]
    if content_language:
        declared_langs['content-language'] = content_language.lower().split('-')[0].split('_')[0]

    if len(set(declared_langs.values())) > 1:
        detail = ', '.join(f'{k}="{v}"' for k, v in declared_langs.items())
        recs.append({
            'severity': 'critical',
            'category': 'locale-consistency',
            'issue': f'Conflicting language declarations detected: {detail}. Search engines receive mixed signals.',
            'recommendation': (
                'Ensure all locale declarations agree on the same language for each page variant. '
                'Conflicting signals confuse search engine crawlers and may result in incorrect '
                'regional indexing.'
            ),
            'codeExample': (
                '<!-- All three should agree -->\n'
                '<html lang="de">\n'
                '<meta property="og:locale" content="de_DE" />\n'
                '<meta http-equiv="content-language" content="de" />'
            ),
        })

    # Also check: detected language vs declared language
    if lang_det.get('results') and lang_attr:
        detected_lang = lang_det['results'][0]['lang']
        declared_base = lang_attr.lower().split('-')[0].split('_')[0]
        detected_conf = lang_det['results'][0].get('confidence', 0)
        if detected_lang != declared_base and detected_conf > 0.7:
            recs.append({
                'severity': 'warning',
                'category': 'locale-consistency',
                'issue': (
                    f'Declared language "{lang_attr}" does not match detected content language '
                    f'"{detected_lang}" (confidence: {detected_conf:.1%}). The page content may '
                    f'be in a different language than declared.'
                ),
                'recommendation': (
                    'Verify the page content matches the declared language. If this is a '
                    'multilingual page, ensure the primary content language matches <html lang>. '
                    'Mixed-language pages should declare the dominant language.'
                ),
                'codeExample': None,
            })

    # ── 4. TLD vs Content Mismatch ──────────────────────────────────────
    if tld and tld in TLD_MAP and primary_lang:
        tld_region = TLD_MAP[tld]
        # Build set of languages expected for this TLD region
        tld_langs = {lc for lc, rc in LANG_TO_REGION.items() if rc == tld_region}
        lang_base = primary_lang.split('-')[0].split('_')[0]

        # Only flag if the detected lang is NOT associated with the TLD's region
        # and it's not English (English content on ccTLD is common for cross-border)
        if lang_base not in tld_langs and lang_base != 'en' and tld_langs:
            tld_lang_names = ', '.join(LANG_NAMES.get(l, l) for l in sorted(tld_langs))
            region_name = COUNTRY_NAMES.get(tld_region, tld_region)
            recs.append({
                'severity': 'warning',
                'category': 'tld-content-mismatch',
                'issue': (
                    f'Country-code TLD "{tld}" suggests {region_name}, but page content is '
                    f'primarily in {LANG_NAMES.get(lang_base, lang_base)}. '
                    f'Expected language(s) for this TLD: {tld_lang_names}.'
                ),
                'recommendation': (
                    'For cross-border sites using a ccTLD, ensure the ccTLD domain serves content '
                    'in the expected local language, or use hreflang tags to indicate this is an '
                    'alternate-language version. Consider using a gTLD (.com) with subdirectories '
                    'or subdomains for multi-region targeting if content doesn\'t match the ccTLD.'
                ),
                'codeExample': (
                    '<!-- Option A: Serve local content on ccTLD -->\n'
                    f'<!-- {tld} domain → provide {tld_lang_names} content -->\n\n'
                    '<!-- Option B: Use gTLD with subdirectories -->\n'
                    '<!-- example.com/de/ for German, example.com/en/ for English -->'
                ),
            })

    # ── 5. IP/Hosting Alignment ─────────────────────────────────────────
    if ip_geo.get('countryCode') and primary_region:
        server_region = ip_geo['countryCode']
        server_country = COUNTRY_NAMES.get(server_region, server_region)
        target_country = COUNTRY_NAMES.get(primary_region, primary_region)

        # Check if ISP is a CDN
        isp_info = (ip_geo.get('isp', '') + ' ' + ip_geo.get('org', '')).lower()
        is_cdn = any(cdn in isp_info for cdn in [
            'cloudflare', 'akamai', 'fastly', 'cloudfront', 'edgecast',
            'stackpath', 'incapsula', 'sucuri', 'google', 'microsoft', 'amazon',
        ])

        if server_region != primary_region and not is_cdn:
            # Different continents = more severe
            recs.append({
                'severity': 'warning',
                'category': 'hosting-alignment',
                'issue': (
                    f'Server is hosted in {server_country} ({server_region}) but target audience '
                    f'is in {target_country} ({primary_region}). No CDN detected. '
                    f'This may cause higher latency for target users.'
                ),
                'recommendation': (
                    'Consider using a CDN (Cloudflare, AWS CloudFront, Fastly) to serve content '
                    'from edge nodes closer to your target audience. For cross-border e-commerce, '
                    'page load speed directly impacts conversion rates.'
                ),
                'codeExample': None,
            })
        elif is_cdn:
            recs.append({
                'severity': 'info',
                'category': 'hosting-alignment',
                'issue': (
                    f'CDN detected ({ip_geo.get("org", "unknown")}). Server resolved to '
                    f'{server_country} but content is likely served from edge nodes globally.'
                ),
                'recommendation': 'CDN is properly configured for cross-border delivery. No action needed.',
                'codeExample': None,
            })

    # ── 6. Charset Issues ───────────────────────────────────────────────
    if not charset:
        recs.append({
            'severity': 'warning',
            'category': 'charset',
            'issue': 'No charset declaration found. Multilingual content (especially CJK, Arabic, Cyrillic) may render incorrectly.',
            'recommendation': (
                'Always declare UTF-8 charset for cross-border sites. Place it as the first '
                'element in <head> to ensure the browser parses all content correctly.'
            ),
            'codeExample': '<meta charset="UTF-8">',
        })
    elif charset.lower().replace('-', '') not in ('utf8', 'utf16'):
        recs.append({
            'severity': 'warning',
            'category': 'charset',
            'issue': (
                f'Charset is "{charset}" instead of UTF-8. Non-UTF-8 encodings cannot reliably '
                f'represent all scripts needed for multilingual cross-border content.'
            ),
            'recommendation': (
                'Migrate to UTF-8 encoding. UTF-8 supports all Unicode scripts and is the '
                'standard for multilingual websites. Update both the meta tag and ensure your '
                'server sends Content-Type: text/html; charset=UTF-8.'
            ),
            'codeExample': '<meta charset="UTF-8">',
        })

    # ── 7. Target Market Adaptation ─────────────────────────────────────
    if primary_region and primary_region in REGION_CURRENCY:
        expected_currencies = REGION_CURRENCY[primary_region]
        found_codes = content_s.get('currencyCodes', [])
        found_symbols = content_s.get('currencySymbols', [])
        all_found = found_codes + found_symbols

        has_local = any(c in all_found for c in expected_currencies)
        if not has_local and found_codes:
            # Has SOME currency but not the local one
            target_name = COUNTRY_NAMES.get(primary_region, primary_region)
            recs.append({
                'severity': 'warning',
                'category': 'market-adaptation',
                'issue': (
                    f'Page targets {target_name} but does not display local currency '
                    f'({", ".join(expected_currencies)}). Found currencies: {", ".join(found_codes)}. '
                    f'Users expect to see prices in their local currency.'
                ),
                'recommendation': (
                    'Display prices in the local currency for each target market. Consider '
                    'implementing a currency switcher or automatic currency conversion based on '
                    'detected region. At minimum, show local currency alongside base currency.'
                ),
                'codeExample': None,
            })

    # Social media adaptation for target region
    if primary_region and primary_region in REGION_SOCIAL:
        expected_socials = REGION_SOCIAL[primary_region]
        found_social_domains = [s.get('domain', '') for s in content_s.get('socialMediaSignals', [])]
        missing_socials = [s for s in expected_socials if s not in found_social_domains]

        if missing_socials:
            target_name = COUNTRY_NAMES.get(primary_region, primary_region)
            recs.append({
                'severity': 'info',
                'category': 'market-adaptation',
                'issue': (
                    f'Page targets {target_name} but does not link to key regional social '
                    f'platforms: {", ".join(missing_socials)}. These platforms are dominant '
                    f'in the target market.'
                ),
                'recommendation': (
                    f'For {target_name} market penetration, consider establishing presence on '
                    f'regional social platforms and linking to them from your site. This builds '
                    f'trust and provides region-appropriate sharing options.'
                ),
                'codeExample': None,
            })

    # ── 9. Cultural & Functional Adaptation ─────────────────────────────
    # Payment Methods
    if primary_region and primary_region in PAYMENT_METHODS:
        expected_methods = PAYMENT_METHODS[primary_region]
        found_methods = [p['method'] for p in content_s.get('paymentMethods', []) if p['region'] == primary_region]

        if not found_methods:
            target_name = COUNTRY_NAMES.get(primary_region, primary_region)
            recs.append({
                'severity': 'info',
                'category': 'market-adaptation',
                'issue': (
                    f'Page targets {target_name} but does not mention popular local payment methods '
                    f'({", ".join(expected_methods)}). Trust signals are crucial for conversion.'
                ),
                'recommendation': (
                    f'Ensure you offer and display logos for {target_name}-specific payment options. '
                    f'Customers in this region strongly prefer these local methods over generic credit cards.'
                ),
                'codeExample': None,
            })

    # Spelling & Vocabulary (US vs UK)
    spelling_counts = content_s.get('spellingCounts', {'US': 0, 'UK': 0})
    us_count = spelling_counts.get('US', 0)
    uk_count = spelling_counts.get('UK', 0)

    if primary_region in ('US', 'PH') and uk_count > us_count and uk_count > 0:
         recs.append({
            'severity': 'info',
            'category': 'cultural-adaptation',
            'issue': (
                f'Page targets {primary_region} but uses British spelling variants (e.g., colour, centre) '
                f'more frequently than American ones.'
            ),
            'recommendation': 'Localize spelling to match the target audience (American English).',
            'codeExample': None,
        })
    elif primary_region in ('GB', 'AU', 'NZ', 'IE', 'ZA') and us_count > uk_count and us_count > 0:
         recs.append({
            'severity': 'info',
            'category': 'cultural-adaptation',
            'issue': (
                f'Page targets {primary_region} but uses American spelling variants (e.g., color, center) '
                f'more frequently than British ones.'
            ),
            'recommendation': 'Localize spelling to match the target audience (British/Commonwealth English).',
            'codeExample': None,
        })

    # Measurement Units
    unit_counts = content_s.get('unitCounts', {'Imperial': 0, 'Metric': 0})
    imp_count = unit_counts.get('Imperial', 0)
    met_count = unit_counts.get('Metric', 0)

    if primary_region == 'US' and met_count > imp_count and met_count > 0:
        recs.append({
            'severity': 'info',
            'category': 'cultural-adaptation',
            'issue': 'Page targets US but uses Metric units (cm, kg) more frequently than Imperial units (inch, lbs).',
            'recommendation': 'Ensure product dimensions and weights are displayed in Imperial units (or both) for US customers.',
            'codeExample': None,
        })
    elif primary_region not in ('US', 'LR', 'MM') and primary_region and imp_count > met_count and imp_count > 0:
        target_name = COUNTRY_NAMES.get(primary_region, primary_region)
        recs.append({
            'severity': 'info',
            'category': 'cultural-adaptation',
            'issue': f'Page targets {target_name} but uses Imperial units (inch, lbs) more frequently than Metric units.',
            'recommendation': 'Ensure product dimensions and weights are displayed in Metric units (cm, kg) for this market.',
            'codeExample': None,
        })

    # ── 10. User Experience (UX) & Accessibility ────────────────────────
    ux_s = content_s.get('uxSignals', {})

    # Viewport
    viewport = ux_s.get('viewport')
    if not viewport:
        recs.append({
            'severity': 'critical',
            'category': 'ux-mobile',
            'issue': 'No viewport meta tag found. The site will not render correctly on mobile devices.',
            'recommendation': 'Add a viewport meta tag to ensure mobile responsiveness.',
            'codeExample': '<meta name="viewport" content="width=device-width, initial-scale=1">',
        })
    elif 'width=device-width' not in viewport and 'initial-scale=1' not in viewport:
        recs.append({
            'severity': 'warning',
            'category': 'ux-mobile',
            'issue': f'Viewport meta tag exists ("{viewport}") but may not be configured for responsive design.',
            'recommendation': 'Ensure viewport is set to "width=device-width, initial-scale=1".',
            'codeExample': '<meta name="viewport" content="width=device-width, initial-scale=1">',
        })

    # Input Types (Mobile Keyboard Optimization)
    inputs = ux_s.get('inputs', [])
    for inp in inputs:
        name = (inp.get('name') or '').lower()
        typ = (inp.get('type') or 'text').lower()

        if 'email' in name and typ != 'email':
             recs.append({
                'severity': 'info',
                'category': 'ux-forms',
                'issue': f'Input field "{name}" uses type="{typ}" instead of type="email".',
                'recommendation': 'Use type="email" to trigger the correct mobile keyboard (with @ symbol).',
                'codeExample': '<input type="email" name="email" ...>',
            })
             break # Only report once

    for inp in inputs:
        name = (inp.get('name') or '').lower()
        typ = (inp.get('type') or 'text').lower()
        if ('phone' in name or 'tel' in name or 'mobile' in name) and typ != 'tel':
             recs.append({
                'severity': 'info',
                'category': 'ux-forms',
                'issue': f'Input field "{name}" uses type="{typ}" instead of type="tel".',
                'recommendation': 'Use type="tel" to trigger the numeric mobile keyboard.',
                'codeExample': '<input type="tel" name="phone" ...>',
            })
             break # Only report once

    # Images (Alt Text & Loading)
    images = ux_s.get('images', [])
    if images:
        missing_alt = sum(1 for img in images if not img.get('alt'))
        if missing_alt > 0 and (missing_alt / len(images)) > 0.5:
             recs.append({
                'severity': 'warning',
                'category': 'accessibility',
                'issue': f'{missing_alt}/{len(images)} sampled images are missing "alt" text.',
                'recommendation': 'Add descriptive alt text to images for screen readers and SEO.',
                'codeExample': '<img src="..." alt="Description of image">',
            })

    # ── 8. Multi-market Coverage ────────────────────────────────────────
    if hreflangs and len(hreflangs) >= 2:
        hreflang_bases = set()
        for h in hreflangs:
            if h.lower() != 'x-default':
                hreflang_bases.add(h.lower().split('-')[0].split('_')[0])

        # Suggest commonly missed major markets
        covered_names = [LANG_NAMES.get(l, l) or l for l in sorted(hreflang_bases)]
        missing_major = []
        for m in MAJOR_MARKETS:
            if m not in hreflang_bases:
                missing_major.append(LANG_NAMES.get(m, m))

        if missing_major and len(missing_major) <= 7:
            recs.append({
                'severity': 'info',
                'category': 'market-coverage',
                'issue': (
                    f'Site covers {len(hreflang_bases)} language(s) via hreflang '
                    f'({", ".join(covered_names)}). Major markets not covered: '
                    f'{", ".join(missing_major)}.'
                ),
                'recommendation': (
                    'Consider expanding to additional major markets based on your traffic data '
                    'and business goals. Each new market should have properly localized content, '
                    'not just machine-translated text.'
                ),
                'codeExample': None,
            })

    # ── Sort by severity ────────────────────────────────────────────────
    severity_order = {'critical': 0, 'warning': 1, 'info': 2}
    recs.sort(key=lambda r: severity_order.get(r['severity'], 9))

    # ── Summary ─────────────────────────────────────────────────────────
    critical_count = sum(1 for r in recs if r['severity'] == 'critical')
    warning_count = sum(1 for r in recs if r['severity'] == 'warning')
    info_count = sum(1 for r in recs if r['severity'] == 'info')

    # Overall score: 100 minus deductions
    score = 100
    score -= critical_count * 20
    score -= warning_count * 10
    score -= info_count * 2
    score = max(score, 0)

    if score >= 80:
        grade = 'A'
    elif score >= 60:
        grade = 'B'
    elif score >= 40:
        grade = 'C'
    elif score >= 20:
        grade = 'D'
    else:
        grade = 'F'

    summary = {
        'score': score,
        'grade': grade,
        'totalIssues': len(recs),
        'critical': critical_count,
        'warnings': warning_count,
        'info': info_count,
    }

    return {'summary': summary, 'recommendations': recs}


# ============================================================================
# Multi-Page Crawling
# ============================================================================

def _normalize_url(url):
    parsed = urllib.parse.urlparse(url)
    normalized = parsed._replace(fragment='')
    path = normalized.path.rstrip('/') or '/'
    normalized = normalized._replace(path=path)
    return urllib.parse.urlunparse(normalized)


def _get_domain(url):
    return urllib.parse.urlparse(url).netloc.lower()


def extract_links(html, base_url):
    base_domain = _get_domain(base_url)
    links = set()

    SKIP_EXTENSIONS = {
        '.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp', '.ico', '.bmp',
        '.css', '.js', '.json', '.xml', '.rss', '.atom',
        '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
        '.zip', '.tar', '.gz', '.rar', '.7z',
        '.mp3', '.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm',
        '.woff', '.woff2', '.ttf', '.eot', '.otf',
    }

    if HAS_BS4:
        soup = BeautifulSoup(html, 'html.parser')
        anchors = soup.find_all('a', href=True)
        raw_hrefs = [a['href'] for a in anchors]
    else:
        raw_hrefs = re.findall(r'<a[^>]+href=["\']([^"\']+)["\']', html, re.IGNORECASE)

    for href in raw_hrefs:
        href = href.strip()

        if href.startswith(('mailto:', 'tel:', 'javascript:', 'data:', '#', 'ftp:')):
            continue

        try:
            absolute = urllib.parse.urljoin(base_url, href)
        except Exception:
            continue

        parsed = urllib.parse.urlparse(absolute)

        if parsed.scheme not in ('http', 'https'):
            continue

        if parsed.netloc.lower() != base_domain:
            continue

        path_lower = parsed.path.lower()
        if any(path_lower.endswith(ext) for ext in SKIP_EXTENSIONS):
            continue

        normalized = _normalize_url(absolute)
        links.add(normalized)

    return list(links)


def crawl_site(start_url, max_depth=3, max_pages=20, timeout=15,
               delay=1.0, progress_callback=None):
    start_normalized = _normalize_url(start_url)
    start_domain = _get_domain(start_url)

    visited = set()
    results = []

    queue = deque([(start_normalized, 0)])
    visited.add(start_normalized)

    while queue and len(results) < max_pages:
        url, depth = queue.popleft()

        if results:
            time.sleep(delay)

        if progress_callback:
            progress_callback(len(results) + 1, url)

        html, final_url, err = fetch_html(url, timeout)
        if not html:
            continue

        results.append({
            'url': url,
            'html': html,
            'depth': depth,
            'final_url': final_url or url,
        })

        if depth < max_depth and len(results) < max_pages:
            new_links = extract_links(html, final_url or url)
            for link in new_links:
                link_normalized = _normalize_url(link)
                if _get_domain(link_normalized) != start_domain:
                    continue
                if link_normalized not in visited:
                    visited.add(link_normalized)
                    queue.append((link_normalized, depth + 1))

    return results


# ============================================================================
# AI Content Analysis
# ============================================================================

def _call_ai_api(messages, api_base, api_key, model='gpt-4o',
                 temperature=0.3, timeout=60):
    api_url = api_base.rstrip('/') + '/chat/completions'

    payload = {
        'model': model,
        'messages': messages,
        'temperature': temperature,
        'response_format': {'type': 'json_object'},
    }

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}',
    }

    body = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(api_url, data=body, headers=headers, method='POST')

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            return data['choices'][0]['message']['content']
    except Exception as e:
        return {'error': str(e)}


def resolve_target_audience(user_input, result, ai_analysis=None):
    """Resolve final target audience with priority: user input > AI > rule-based."""
    normalized_user_input = (user_input or '').strip()
    if normalized_user_input:
        return {
            'source': 'user_input',
            'userInput': normalized_user_input,
            'inferredAudience': None,
            'finalAudience': normalized_user_input,
        }

    inferred = None
    if isinstance(ai_analysis, dict):
        ta = ai_analysis.get('targetAudience', {})
        inferred = ta.get('finalAudience') or ta.get('inferredAudience')
        if not inferred:
            inferred = ai_analysis.get('inferredAudience')
        if isinstance(inferred, str):
            inferred = inferred.strip() or None
        else:
            inferred = None

    if inferred:
        return {
            'source': 'ai_inferred',
            'userInput': None,
            'inferredAudience': inferred,
            'finalAudience': inferred,
        }

    likely = None
    if isinstance(result, dict):
        likely = result.get('likelyAudience')
        if isinstance(likely, str):
            likely = likely.strip() or None
        else:
            likely = None

    if likely:
        return {
            'source': 'rule_based',
            'userInput': None,
            'inferredAudience': likely,
            'finalAudience': likely,
        }

    return {
        'source': 'rule_based',
        'userInput': None,
        'inferredAudience': 'Unknown audience',
        'finalAudience': 'Unknown audience',
    }


def build_fallback_persona_analysis(result, evidence, target_audience=None):
    """Build deterministic persona analysis when AI analysis is unavailable."""
    result = result or {}
    evidence = evidence or {}
    audience = resolve_target_audience(target_audience, result, ai_analysis=None)

    region_code = result.get('primaryRegion') or 'N/A'
    region_name = result.get('primaryRegionName') or 'Unknown'
    language_name = result.get('primaryLanguageName') or 'Unknown'

    confidence = result.get('regionConfidence', 0.0) or 0.0
    base_score = max(0.0, min(10.0, round(float(confidence) * 10, 1)))

    html_signals = evidence.get('htmlSignals', {})
    content_signals = evidence.get('contentSignals', {})

    matching_signals = []
    mismatch_signals = []

    if html_signals.get('lang'):
        matching_signals.append(f"声明了页面语言：{html_signals.get('lang')}")
        base_score += 0.4
    else:
        mismatch_signals.append("未声明 <html lang>，语言定位不够清晰")

    currencies = content_signals.get('currencySymbols', []) + content_signals.get('currencyCodes', [])
    if currencies:
        dedup_currencies = list(dict.fromkeys(currencies))
        matching_signals.append(f"检测到货币信号：{', '.join(dedup_currencies[:3])}")
        base_score += 0.6

    hreflangs = html_signals.get('hreflangTags', [])
    if hreflangs:
        matching_signals.append("存在 hreflang 标签，支持多地区人群识别")
        base_score += 0.4
    else:
        mismatch_signals.append("缺少 hreflang 标签，多地区人群覆盖信息不足")

    if not content_signals.get('paymentMethods'):
        mismatch_signals.append("页面未呈现明显的本地化支付方式信号")
    else:
        matching_signals.append("检测到本地支付方式信号")
        base_score += 0.3

    final_score = max(0.0, min(10.0, round(base_score, 1)))

    persona = {
        'regionCode': region_code,
        'regionName': region_name,
        'language': language_name,
        'personaLabel': f"{region_name} {audience.get('finalAudience', 'target audience')}",
        'traits': [
            '关注价格和价值比',
            '偏好清晰的配送与退换货信息',
            '倾向于移动端快速决策',
        ],
        'motivations': [
            '获得与本地区匹配的商品和文案',
            '降低支付和履约不确定性',
        ],
        'painPoints': [
            '语言/货币信息不一致导致决策成本高',
            '本地化信任要素不足（评价、保障、支付）',
        ],
        'purchaseDrivers': [
            '价格透明',
            '本地支付方式',
            '快速物流和明确售后',
        ],
    }

    summary = (
        "网站与该人群匹配度较好。"
        if final_score >= 7
        else "网站与该人群存在部分匹配缺口，建议优先修复本地化关键要素。"
    )

    return {
        'audience': audience,
        'regionalPersona': persona,
        'personaFit': {
            'score': final_score,
            'isFit': final_score >= 7,
            'matchingSignals': matching_signals[:10],
            'mismatchSignals': mismatch_signals[:10],
            'summary': summary,
        },
    }


def compose_persona_analysis(result, evidence, target_audience=None, ai_analysis=None, persona_context=None):
    """Compose persona analysis with optional persona context for enhanced evaluation."""
    # If persona_context is provided, use it directly
    if persona_context:
        audience = {
            'source': persona_context.get('source', 'rule_based'),
            'userInput': persona_context.get('userInput'),
            'inferredAudience': persona_context.get('inferredAudience'),
            'finalAudience': persona_context.get('finalAudience'),
        }
    else:
        # Fallback to original logic
        fallback = build_fallback_persona_analysis(result, evidence, target_audience=target_audience)
        audience = fallback['audience']

    if not isinstance(ai_analysis, dict) or 'error' in ai_analysis:
        fallback = build_fallback_persona_analysis(result, evidence, target_audience=target_audience)
        return fallback

    regional_persona = ai_analysis.get('regionalPersona')
    persona_fit = ai_analysis.get('personaFit')

    if not isinstance(regional_persona, dict):
        fallback = build_fallback_persona_analysis(result, evidence, target_audience=target_audience)
        regional_persona = fallback['regionalPersona']
    if not isinstance(persona_fit, dict):
        fallback = build_fallback_persona_analysis(result, evidence, target_audience=target_audience)
        persona_fit = fallback['personaFit']

    return {
        'audience': audience,
        'regionalPersona': regional_persona,
        'personaFit': {
            'score': persona_fit.get('score', fallback['personaFit'].get('score')),
            'isFit': persona_fit.get('isFit', fallback['personaFit'].get('isFit')),
            'matchingSignals': persona_fit.get('matchingSignals', fallback['personaFit'].get('matchingSignals', [])),
            'mismatchSignals': persona_fit.get('mismatchSignals', fallback['personaFit'].get('mismatchSignals', [])),
            'summary': persona_fit.get('summary', fallback['personaFit'].get('summary')),
        },
    }


AI_CONTENT_ANALYSIS_PROMPT = """\
You are an expert in cross-border e-commerce localization and multilingual content quality analysis.

Analyze the following web page content and provide a structured assessment.

## Context
- **Page URL**: {url}
- **Detected Region**: {region} ({region_name})
- **Detected Language**: {language} ({language_name})
- **Region Confidence**: {confidence}
- **User-Provided Target Audience**: {target_audience}

## Page Content (truncated to first 3000 chars):
```
{content}
```

## Your Task

Analyze the content and return a JSON object with EXACTLY this structure:

{{
  "targetAudience": {{
    "inferredAudience": "Who this website appears to target based on content and value proposition",
    "finalAudience": "Use user-provided target audience if present, otherwise use inferredAudience"
  }},
  "regionalPersona": {{
    "regionCode": "{region}",
    "regionName": "{region_name}",
    "language": "{language_name}",
    "personaLabel": "One-sentence persona label for this region + audience",
    "traits": ["Trait 1", "Trait 2", "Trait 3"],
    "motivations": ["Motivation 1", "Motivation 2"],
    "painPoints": ["Pain point 1", "Pain point 2"],
    "purchaseDrivers": ["Driver 1", "Driver 2", "Driver 3"]
  }},
  "personaFit": {{
    "score": <1-10 float, 10=website perfectly matches this persona>,
    "isFit": <true/false>,
    "matchingSignals": ["Signals that match persona needs"],
    "mismatchSignals": ["Signals that do not match persona needs"],
    "summary": "Concise summary of fit between website and persona"
  }},
  "inferredProductType": "Brief description of what this website/page is about (e.g., 'Fashion e-commerce', 'SaaS project management tool', 'News portal')",
  "languageQuality": {{
    "score": <1-10 float, 10=perfect native quality>,
    "isNativeLevel": <true/false>,
    "machineTranslationDetected": <true/false>,
    "details": "Explain your assessment: grammar quality, naturalness, vocabulary appropriateness for the target region"
  }},
  "regionFit": {{
    "score": <1-10 float, 10=perfectly adapted for target region>,
    "culturallyApproriate": <true/false>,
    "issues": ["List specific issues, e.g., 'Uses US date format MM/DD for German audience', 'Mentions Thanksgiving sale for Japanese market'"],
    "strengths": ["List what's done well, e.g., 'Uses local currency correctly', 'References local holidays'"]
  }},
  "contentProductAlignment": {{
    "score": <1-10 float, 10=content perfectly matches product positioning>,
    "details": "Does the copy, tone, and messaging match what the product/service is? Is the value proposition clear for the target audience?"
  }},
  "suggestions": [
    "Actionable suggestion 1 for improving localization quality",
    "Actionable suggestion 2...",
    "..."
  ]
}}

IMPORTANT:
- Respond ONLY with valid JSON, no markdown wrapping.
- If the content is too short to assess, still provide your best estimate and note the limitation.
- Focus on whether the content feels natural to a native speaker of the target region.
- Check for: machine translation artifacts, cultural mismatches, inappropriate idioms, wrong date/number formats, missing local context.
"""


def analyze_content_with_ai(text_content, url, result, api_base, api_key,
                            model='gpt-4o', timeout=60, target_audience=None):
    if not text_content or len(text_content.strip()) < 20:
        return {'error': 'Insufficient text content for AI analysis'}

    region = result.get('primaryRegion', 'Unknown')
    region_name = result.get('primaryRegionName', 'Unknown')
    language = result.get('primaryLanguage', 'Unknown')
    language_name = result.get('primaryLanguageName', 'Unknown')
    confidence = result.get('regionConfidence', 0)

    prompt = AI_CONTENT_ANALYSIS_PROMPT.format(
        url=url,
        region=region,
        region_name=region_name,
        language=language,
        language_name=language_name,
        confidence=confidence,
        target_audience=(target_audience.strip() if isinstance(target_audience, str) and target_audience.strip() else 'Not provided'),
        content=text_content[:3000],
    )

    messages = [
        {'role': 'system', 'content': 'You are a multilingual content quality analyst. Always respond with valid JSON.'},
        {'role': 'user', 'content': prompt},
    ]

    raw_reply = _call_ai_api(messages, api_base, api_key, model=model,
                             timeout=timeout)

    if isinstance(raw_reply, dict) and 'error' in raw_reply:
        return raw_reply

    try:
        analysis = json.loads(raw_reply)
        analysis['targetAudience'] = resolve_target_audience(
            target_audience, result, ai_analysis=analysis
        )
        return analysis
    except json.JSONDecodeError:
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw_reply, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        return {'error': 'Failed to parse AI response as JSON', 'rawReply': raw_reply[:500]}


# ============================================================================
# Site-Level Aggregation
# ============================================================================

def aggregate_site_results(page_results):
    if not page_results:
        return None

    all_scores = {}
    total_max_weight = 0.0
    lang_counts = {}
    region_counts = {}

    for pr in page_results:
        result = pr.get('result')
        if not result:
            continue

        breakdown = result.get('signalBreakdown', {})
        for region, score in breakdown.items():
            all_scores[region] = all_scores.get(region, 0) + score

        pr_region = result.get('primaryRegion')
        pr_lang = result.get('primaryLanguage')
        if pr_region:
            region_counts[pr_region] = region_counts.get(pr_region, 0) + 1
        if pr_lang:
            lang_counts[pr_lang] = lang_counts.get(pr_lang, 0) + 1

    if all_scores:
        primary_region = max(all_scores, key=lambda k: all_scores[k])
    else:
        primary_region = None

    if lang_counts:
        primary_lang = max(lang_counts, key=lambda k: lang_counts[k])
    else:
        primary_lang = None

    num_pages = len([pr for pr in page_results if pr.get('result')])
    if primary_region and num_pages > 0:
        agree_count = region_counts.get(primary_region, 0)
        consistency = round(agree_count / num_pages, 2)
    else:
        consistency = 0.0

    confidences = [
        pr['result']['regionConfidence']
        for pr in page_results
        if pr.get('result') and pr['result'].get('regionConfidence') is not None
    ]
    avg_confidence = round(sum(confidences) / len(confidences), 2) if confidences else 0.0

    country_name = COUNTRY_NAMES.get(primary_region, primary_region) if primary_region else None
    lang_name = LANG_NAMES.get(primary_lang, primary_lang) if primary_lang else None

    if primary_region and primary_lang:
        audience = f"{lang_name}-speaking audience in {country_name}"
    elif primary_region:
        audience = f"Audience in {country_name}"
    else:
        audience = "Unknown"

    return {
        'primaryRegion': primary_region,
        'primaryRegionName': country_name,
        'primaryLanguage': primary_lang,
        'primaryLanguageName': lang_name,
        'likelyAudience': audience,
        'regionConfidence': avg_confidence,
        'regionConsistency': consistency,
        'pagesAnalyzed': num_pages,
        'regionDistribution': {
            k: round(v, 3)
            for k, v in sorted(all_scores.items(), key=lambda x: -x[1])
        },
        'languageDistribution': lang_counts,
    }


def aggregate_site_optimization(page_results):
    seen = set()
    all_recs = []

    for pr in page_results:
        opt = pr.get('optimization')
        if not opt:
            continue
        for rec in opt.get('recommendations', []):
            dedup_key = (rec['severity'], rec['category'], rec['issue'][:80])
            if dedup_key not in seen:
                seen.add(dedup_key)
                all_recs.append(rec)

    severity_order = {'critical': 0, 'warning': 1, 'info': 2}
    all_recs.sort(key=lambda r: severity_order.get(r['severity'], 9))

    critical_count = sum(1 for r in all_recs if r['severity'] == 'critical')
    warning_count = sum(1 for r in all_recs if r['severity'] == 'warning')
    info_count = sum(1 for r in all_recs if r['severity'] == 'info')

    score = 100
    score -= critical_count * 20
    score -= warning_count * 10
    score -= info_count * 2
    score = max(score, 0)

    if score >= 80:
        grade = 'A'
    elif score >= 60:
        grade = 'B'
    elif score >= 40:
        grade = 'C'
    elif score >= 20:
        grade = 'D'
    else:
        grade = 'F'

    return {
        'summary': {
            'score': score,
            'grade': grade,
            'totalIssues': len(all_recs),
            'critical': critical_count,
            'warnings': warning_count,
            'info': info_count,
        },
        'recommendations': all_recs,
    }


def aggregate_ai_analysis(page_ai_results):
    valid_results = [r for r in page_ai_results if r and 'error' not in r]
    if not valid_results:
        return {'error': 'No valid AI analysis results to aggregate'}

    lang_scores = [r['languageQuality']['score'] for r in valid_results
                   if 'languageQuality' in r and 'score' in r.get('languageQuality', {})]
    region_scores = [r['regionFit']['score'] for r in valid_results
                     if 'regionFit' in r and 'score' in r.get('regionFit', {})]
    alignment_scores = [r['contentProductAlignment']['score'] for r in valid_results
                        if 'contentProductAlignment' in r and 'score' in r.get('contentProductAlignment', {})]

    product_types = list(dict.fromkeys(
        r.get('inferredProductType', '') for r in valid_results
        if r.get('inferredProductType')
    ))

    mt_detected = any(
        r.get('languageQuality', {}).get('machineTranslationDetected', False)
        for r in valid_results
    )

    all_native = all(
        r.get('languageQuality', {}).get('isNativeLevel', False)
        for r in valid_results
    )

    all_issues = list(dict.fromkeys(
        issue
        for r in valid_results
        for issue in r.get('regionFit', {}).get('issues', [])
        if issue
    ))

    all_strengths = list(dict.fromkeys(
        s
        for r in valid_results
        for s in r.get('regionFit', {}).get('strengths', [])
        if s
    ))

    all_suggestions = list(dict.fromkeys(
        s
        for r in valid_results
        for s in r.get('suggestions', [])
        if s
    ))

    return {
        'inferredProductTypes': product_types,
        'pagesAnalyzed': len(valid_results),
        'languageQuality': {
            'averageScore': round(sum(lang_scores) / len(lang_scores), 1) if lang_scores else None,
            'isNativeLevel': all_native,
            'machineTranslationDetected': mt_detected,
        },
        'regionFit': {
            'averageScore': round(sum(region_scores) / len(region_scores), 1) if region_scores else None,
            'issues': all_issues[:20],
            'strengths': all_strengths[:20],
        },
        'contentProductAlignment': {
            'averageScore': round(sum(alignment_scores) / len(alignment_scores), 1) if alignment_scores else None,
        },
        'suggestions': all_suggestions[:20],
    }


def aggregate_persona_analysis(page_persona_results):
    valid = [p for p in page_persona_results if isinstance(p, dict)]
    if not valid:
        return None

    fit_scores = []
    audience_sources = []
    audience_values = []
    traits = []
    matching = []
    mismatching = []

    for item in valid:
        audience = item.get('audience', {})
        persona = item.get('regionalPersona', {})
        fit = item.get('personaFit', {})

        source = audience.get('source')
        if source:
            audience_sources.append(source)

        final_audience = audience.get('finalAudience')
        if final_audience:
            audience_values.append(final_audience)

        score = fit.get('score')
        if isinstance(score, (int, float)):
            fit_scores.append(float(score))

        traits.extend(persona.get('traits', []))
        matching.extend(fit.get('matchingSignals', []))
        mismatching.extend(fit.get('mismatchSignals', []))

    source = (
        'user_input' if 'user_input' in audience_sources
        else 'ai_inferred' if 'ai_inferred' in audience_sources
        else 'rule_based'
    )

    # Preserve first-seen order while deduping
    traits = list(dict.fromkeys([t for t in traits if t]))
    matching = list(dict.fromkeys([m for m in matching if m]))
    mismatching = list(dict.fromkeys([m for m in mismatching if m]))
    audience_values = list(dict.fromkeys([a for a in audience_values if a]))

    representative_persona = valid[0].get('regionalPersona', {})
    avg_score = round(sum(fit_scores) / len(fit_scores), 1) if fit_scores else None

    return {
        'audience': {
            'source': source,
            'userInput': None,
            'inferredAudience': audience_values[0] if audience_values else None,
            'finalAudience': audience_values[0] if audience_values else 'Unknown audience',
        },
        'regionalPersona': {
            'regionCode': representative_persona.get('regionCode'),
            'regionName': representative_persona.get('regionName'),
            'language': representative_persona.get('language'),
            'personaLabel': representative_persona.get('personaLabel'),
            'traits': traits[:10],
            'motivations': representative_persona.get('motivations', []),
            'painPoints': representative_persona.get('painPoints', []),
            'purchaseDrivers': representative_persona.get('purchaseDrivers', []),
        },
        'personaFit': {
            'score': avg_score,
            'isFit': bool(avg_score is not None and avg_score >= 7),
            'matchingSignals': matching[:20],
            'mismatchSignals': mismatching[:20],
            'summary': (
                "全站整体较符合目标 persona。"
                if avg_score is not None and avg_score >= 7
                else "全站与目标 persona 存在明显差距，建议优先修复关键本地化缺口。"
            ),
        },
    }


# ============================================================================
# Persona-Driven Analysis Context
# ============================================================================

def create_persona_context(target_audience_result):
    """Create a structured persona context for analysis focus."""
    if not target_audience_result:
        return None
    
    source = target_audience_result.get('source', 'rule_based')
    final_audience = target_audience_result.get('finalAudience', '')
    
    # Define persona characteristics based on audience
    persona_focus = {
        'price_sensitive': False,
        'mobile_first': False,
        'local_trust': False,
    }
    
    # Detect focus areas based on audience keywords
    audience_lower = final_audience.lower() if final_audience else ''
    
    if any(kw in audience_lower for kw in ['价格', '便宜', '优惠', 'discount', 'save', 'value', '性价比']):
        persona_focus['price_sensitive'] = True
    
    if any(kw in audience_lower for kw in ['手机', '移动', 'mobile', 'app', '快速', 'quick']):
        persona_focus['mobile_first'] = True
    
    if any(kw in audience_lower for kw in ['本地', '当地', '信任', 'review', '评价', '保障']):
        persona_focus['local_trust'] = True
    
    return {
        'source': source,
        'finalAudience': final_audience,
        'focusAreas': persona_focus,
    }


# ============================================================================
# Site-Level Analysis Orchestrator
# ============================================================================

def analyze_site(url, max_depth=3, max_pages=20, include_ip_geo=True,
                 nlpcloud_token=None, timeout=15, include_recommendations=True,
                 ai_api_base=None, ai_api_key=None, ai_model='gpt-4o',
                 target_audience=None):
    output = {
        'url': url,
        'mode': 'site',
        'analyzedAt': datetime.now(timezone.utc).isoformat(),
        'crawlSummary': None,
        'siteResult': None,
        'siteOptimization': None,
        'aiContentAnalysis': None,
        'personaAnalysis': None,
        'pages': [],
        'errors': [],
        'warnings': [],
    }

    # 0. Resolve target audience FIRST (Persona-driven approach)
    print("Resolving target audience...", file=sys.stderr)
    initial_result = None
    if include_ip_geo:
        domain = urllib.parse.urlparse(url).netloc
        shared_ip_geo = get_ip_geo(domain)
        if 'error' not in shared_ip_geo:
            initial_result = {
                'primaryRegion': shared_ip_geo.get('countryCode'),
                'primaryRegionName': shared_ip_geo.get('country'),
                'primaryLanguage': 'en',  # Default assumption
                'primaryLanguageName': 'English',
                'likelyAudience': 'Unknown audience',
            }
    
    target_audience_result = resolve_target_audience(
        target_audience,
        initial_result
    )
    
    persona_context = create_persona_context(target_audience_result)
    
    if persona_context:
        print(f"Target audience: {persona_context['finalAudience']} (source: {persona_context['source']})", file=sys.stderr)
        focus_areas = persona_context.get('focusAreas', {})
        if any(focus_areas.values()):
            focus_list = [k for k, v in focus_areas.items() if v]
            print(f"Persona focus areas: {', '.join(focus_list)}", file=sys.stderr)

    # 1. Crawl
    def _progress(count, page_url):
        print(f"  [{count}/{max_pages}] Crawling: {page_url}", file=sys.stderr)

    print(f"Crawling {url} (max_depth={max_depth}, max_pages={max_pages})...",
          file=sys.stderr)

    crawled = crawl_site(
        url, max_depth=max_depth, max_pages=max_pages,
        timeout=timeout, delay=1.0, progress_callback=_progress,
    )

    if not crawled:
        output['errors'].append(f"Crawl failed: no pages could be fetched from {url}")
        return output

    output['crawlSummary'] = {
        'pagesAnalyzed': len(crawled),
        'maxDepthReached': max(c['depth'] for c in crawled),
        'pageUrls': [c['url'] for c in crawled],
    }

    print(f"Crawled {len(crawled)} pages. Analyzing...", file=sys.stderr)

    # IP geolocation only once — all pages share the same domain IP
    shared_ip_geo = None
    if include_ip_geo:
        domain = urllib.parse.urlparse(url).netloc
        shared_ip_geo = get_ip_geo(domain)
        if 'error' in shared_ip_geo:
            output['warnings'].append(f"IP geolocation warning: {shared_ip_geo['error']}")

    # 3. Analyze each page
    page_results = []
    page_ai_results = []
    page_persona_results = []

    print(f"Analyzing {len(crawled)} pages with persona focus...", file=sys.stderr)

    for i, page in enumerate(crawled):
        page_url = page['final_url']
        page_html = page['html']
        page_depth = page['depth']

        print(f"  [{i+1}/{len(crawled)}] Analyzing: {page_url}", file=sys.stderr)

        page_output = {
            'url': page_url,
            'depth': page_depth,
            'result': None,
            'evidence': {},
            'optimization': None,
            'aiContentAnalysis': None,
            'personaAnalysis': None,
            'errors': [],
            'warnings': [],
        }

        text_content = ""
        try:
            signals, text_content = extract_signals(page_html, page_url)
            page_output['evidence'].update(signals)
        except Exception as e:
            page_output['errors'].append(f"Signal extraction failed: {e}")

        # NEW: Extract persona-enhanced signals
        if persona_context and text_content:
            try:
                enhanced = extract_persona_enhanced_signals(
                    page_html, 
                    text_content, 
                    persona_context.get('focusAreas', {})
                )
                page_output['evidence']['contentSignals']['enhanced'] = enhanced
            except Exception as e:
                page_output['warnings'].append(f"Persona-enhanced signal extraction failed: {e}")

        if shared_ip_geo:
            page_output['evidence']['ipGeolocation'] = shared_ip_geo

        if text_content and len(text_content.strip()) >= 10:
            ld = {}
            if nlpcloud_token:
                ld = detect_language_nlpcloud(text_content, nlpcloud_token)
                ld['method'] = 'nlpcloud'
            elif HAS_LANGDETECT:
                ld = detect_language_offline(text_content)
                ld['method'] = 'langdetect'
            else:
                ld = {'error': 'No language detection available', 'method': 'none'}
            page_output['evidence']['languageDetection'] = ld
            if 'error' in ld:
                page_output['warnings'].append(f"Language detection: {ld['error']}")
        else:
            page_output['warnings'].append('Insufficient visible text for language detection')
            page_output['evidence']['languageDetection'] = {
                'error': 'Insufficient text', 'method': 'none',
            }

        page_output['result'] = compute_result(page_output['evidence'])

        if include_recommendations and page_output['result']:
            page_output['optimization'] = generate_recommendations(
                page_output['evidence'], page_output['result']
            )

        if ai_api_base and ai_api_key and page_output['result']:
            print(f"    AI analyzing content...", file=sys.stderr)
            ai_result = analyze_content_with_ai(
                text_content, page_url, page_output['result'],
                ai_api_base, ai_api_key, model=ai_model, timeout=timeout,
                target_audience=target_audience,
            )
            page_output['aiContentAnalysis'] = ai_result
            if isinstance(ai_result, dict) and 'error' not in ai_result:
                page_ai_results.append(ai_result)
            if isinstance(ai_result, dict) and 'error' in ai_result:
                page_output['warnings'].append(f"AI analysis: {ai_result['error']}")

        page_output['personaAnalysis'] = compose_persona_analysis(
            page_output.get('result'),
            page_output.get('evidence', {}),
            target_audience=target_audience,
            ai_analysis=page_output.get('aiContentAnalysis'),
            persona_context=persona_context,  # ← Pass persona_context
        )
        page_persona_results.append(page_output['personaAnalysis'])

        page_results.append(page_output)
        output['pages'].append(page_output)

    output['siteResult'] = aggregate_site_results(page_results)

    if include_recommendations:
        output['siteOptimization'] = aggregate_site_optimization(page_results)

    if page_ai_results:
        output['aiContentAnalysis'] = aggregate_ai_analysis(page_ai_results)

    if page_persona_results:
        output['personaAnalysis'] = aggregate_persona_analysis(page_persona_results)

    print(f"Analysis complete. {len(crawled)} pages analyzed.", file=sys.stderr)

    return output


# ============================================================================
# Main
# ============================================================================

def analyze(url, include_ip_geo=True, nlpcloud_token=None, timeout=15,
            include_recommendations=True, ai_api_base=None, ai_api_key=None,
            ai_model='gpt-4o', target_audience=None):
    output = {
        'url': url,
        'mode': 'page',
        'analyzedAt': datetime.now(timezone.utc).isoformat(),
        'result': None,
        'evidence': {},
        'personaAnalysis': None,
        'errors': [],
        'warnings': [],
    }

    # 0. Resolve target audience FIRST (Persona-driven approach)
    print("Resolving target audience...", file=sys.stderr)
    initial_result = None
    if include_ip_geo:
        domain = urllib.parse.urlparse(url).netloc
        geo = get_ip_geo(domain)
        if 'error' not in geo:
            initial_result = {
                'primaryRegion': geo.get('countryCode'),
                'primaryRegionName': geo.get('country'),
                'primaryLanguage': 'en',  # Default assumption
                'primaryLanguageName': 'English',
                'likelyAudience': 'Unknown audience',
            }
    
    target_audience_result = resolve_target_audience(
        target_audience,
        initial_result
    )
    
    persona_context = create_persona_context(target_audience_result)
    
    if persona_context:
        print(f"Target audience: {persona_context['finalAudience']} (source: {persona_context['source']})", file=sys.stderr)
        focus_areas = persona_context.get('focusAreas', {})
        if any(focus_areas.values()):
            focus_list = [k for k, v in focus_areas.items() if v]
            print(f"Persona focus areas: {', '.join(focus_list)}", file=sys.stderr)

    # 1. Fetch HTML
    html, final_url, fetch_err = fetch_html(url, timeout)
    if not html:
        output['errors'].append(f"Failed to fetch HTML: {fetch_err}")
        return output
    if final_url and final_url != url:
        output['warnings'].append(f"Redirected to: {final_url}")

    # 2. Extract Signals
    try:
        signals, text_content = extract_signals(html, final_url or url)
        output['evidence'].update(signals)
    except Exception as e:
        output['errors'].append(f"Signal extraction failed: {e}")
        text_content = ""

    # 2.5. NEW: Extract persona-enhanced signals
    persona_context = None
    if target_audience or include_ip_geo:
        # Create minimal persona context for single-page analysis
        initial_result = None
        if include_ip_geo:
            domain = urllib.parse.urlparse(final_url or url).netloc
            geo = get_ip_geo(domain)
            if 'error' not in geo:
                initial_result = {
                    'primaryRegion': geo.get('countryCode'),
                    'primaryRegionName': geo.get('country'),
                    'primaryLanguage': 'en',
                    'primaryLanguageName': 'English',
                    'likelyAudience': 'Unknown audience',
                }
        
        target_audience_result = resolve_target_audience(
            target_audience,
            initial_result
        )
        persona_context = create_persona_context(target_audience_result)
        
        # Extract enhanced signals
        if persona_context and text_content:
            try:
                enhanced = extract_persona_enhanced_signals(
                    html,
                    text_content,
                    persona_context.get('focusAreas', {})
                )
                output['evidence']['contentSignals']['enhanced'] = enhanced
            except Exception as e:
                output['warnings'].append(f"Persona-enhanced signal extraction failed: {e}")

    # 3. IP Geolocation
    if include_ip_geo:
        domain = urllib.parse.urlparse(url).netloc
        geo = get_ip_geo(domain)
        output['evidence']['ipGeolocation'] = geo
        if 'error' in geo:
            output['warnings'].append(f"IP geolocation warning: {geo['error']}")

    # 4. Language Detection
    if text_content and len(text_content.strip()) >= 10:
        ld: dict = {}
        if nlpcloud_token:
            ld = detect_language_nlpcloud(text_content, nlpcloud_token)
            ld['method'] = 'nlpcloud'
        elif HAS_LANGDETECT:
            ld = detect_language_offline(text_content)
            ld['method'] = 'langdetect'
        else:
            ld = {'error': 'No language detection available', 'method': 'none'}
        output['evidence']['languageDetection'] = ld
        if 'error' in ld:
            output['warnings'].append(f"Language detection: {ld['error']}")
    else:
        output['warnings'].append('Insufficient visible text for language detection')
        output['evidence']['languageDetection'] = {
            'error': 'Insufficient text', 'method': 'none',
        }

    # 5. Compute result
    output['result'] = compute_result(output['evidence'])

    # 6. Cross-border optimization recommendations
    if include_recommendations and output['result']:
        output['optimization'] = generate_recommendations(
            output['evidence'], output['result']
        )

    # 7. AI content analysis (single page)
    if ai_api_base and ai_api_key and output['result']:
        ai_result = analyze_content_with_ai(
            text_content, final_url or url, output['result'],
            ai_api_base, ai_api_key, model=ai_model, timeout=timeout,
            target_audience=target_audience,
        )
        output['aiContentAnalysis'] = ai_result
        if isinstance(ai_result, dict) and 'error' in ai_result:
            output['warnings'].append(f"AI analysis: {ai_result['error']}")

    output['personaAnalysis'] = compose_persona_analysis(
        output.get('result'),
        output.get('evidence', {}),
        target_audience=target_audience,
        ai_analysis=output.get('aiContentAnalysis'),
    )

    return output


def main():
    parser = argparse.ArgumentParser(
        description='Analyze web page for region and audience signals',
    )
    parser.add_argument('url', help='URL to analyze')
    parser.add_argument('--no-ip-geo', action='store_true',
                        help='Disable IP geolocation')
    parser.add_argument('--nlpcloud-token',
                        help='NLP Cloud API token for language detection')
    parser.add_argument('--timeout', type=int, default=15,
                        help='HTTP request timeout in seconds')
    parser.add_argument('--output', '-o',
                        help='Output file path (default: stdout; markdown defaults to Downloads)')
    parser.add_argument('--format', choices=['json', 'markdown'], default='json',
                        help='Output format: json or markdown (default: json)')
    parser.add_argument('--no-recommendations', action='store_true',
                        help='Disable cross-border optimization recommendations')
    parser.add_argument('--target-audience',
                        help='Optional target audience input. If omitted, AI (or rule-based fallback) will infer audience before persona fit analysis.')

    crawl_group = parser.add_argument_group('multi-page crawling')
    crawl_group.add_argument('--no-crawl', action='store_true',
                             help='Disable multi-page site crawling (analyze single page only)')
    crawl_group.add_argument('--max-depth', type=int, default=3,
                             help='Maximum crawl depth (default: 3)')
    crawl_group.add_argument('--max-pages', type=int, default=50,
                             help='Maximum pages to crawl (default: 50)')

    ai_group = parser.add_argument_group('AI content analysis')
    ai_group.add_argument('--ai-api-base',
                          default=os.environ.get('AI_API_BASE'),
                          help='OpenAI-compatible API base URL (or AI_API_BASE env var)')
    ai_group.add_argument('--ai-api-key',
                          default=os.environ.get('AI_API_KEY'),
                          help='API key for AI content analysis (or AI_API_KEY env var)')
    ai_group.add_argument('--ai-model', default='gpt-4o',
                          help='AI model name (default: gpt-4o)')

    args = parser.parse_args()

    # Default to multi-page crawling mode
    if not args.no_crawl:
        result = analyze_site(
            args.url,
            max_depth=args.max_depth,
            max_pages=args.max_pages,
            include_ip_geo=not args.no_ip_geo,
            nlpcloud_token=args.nlpcloud_token,
            timeout=args.timeout,
            include_recommendations=not args.no_recommendations,
            ai_api_base=args.ai_api_base,
            ai_api_key=args.ai_api_key,
            ai_model=args.ai_model,
            target_audience=args.target_audience,
        )
    else:
        result = analyze(
            args.url,
            include_ip_geo=not args.no_ip_geo,
            nlpcloud_token=args.nlpcloud_token,
            timeout=args.timeout,
            include_recommendations=not args.no_recommendations,
            ai_api_base=args.ai_api_base,
            ai_api_key=args.ai_api_key,
            ai_model=args.ai_model,
            target_audience=args.target_audience,
        )

    # Format output
    if args.format == 'markdown':
        # Import markdown generator
        import subprocess
        import tempfile

        # Save JSON to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as tmp:
            json.dump(result, tmp, indent=2, ensure_ascii=False)
            tmp_path = tmp.name

        # Generate markdown
        script_dir = os.path.dirname(os.path.abspath(__file__))
        md_script = os.path.join(script_dir, 'generate_markdown_report.py')

        try:
            md_output = subprocess.check_output(
                ['python3', md_script, tmp_path],
                encoding='utf-8'
            )
            out = md_output
        except Exception as e:
            print(f"Warning: Failed to generate markdown: {e}", file=sys.stderr)
            print("Falling back to JSON output", file=sys.stderr)
            out = json.dumps(result, indent=2, ensure_ascii=False)
        finally:
            os.unlink(tmp_path)
    else:
        out = json.dumps(result, indent=2, ensure_ascii=False)

    output_path = args.output
    if args.format == 'markdown' and not output_path:
        if build_default_markdown_output_path:
            output_path = build_default_markdown_output_path(args.url)
        else:
            fallback_name = f"web-region-audience-report-{datetime.now().strftime('%Y%m%d-%H%M%S')}.md"
            output_path = os.path.join(os.path.expanduser('~'), 'Downloads', fallback_name)

    if output_path:
        output_dir = os.path.dirname(os.path.abspath(output_path))
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(out)
        if args.format == 'markdown':
            print(f"Markdown report saved to: {output_path}")
    else:
        print(out)


if __name__ == '__main__':
    main()
