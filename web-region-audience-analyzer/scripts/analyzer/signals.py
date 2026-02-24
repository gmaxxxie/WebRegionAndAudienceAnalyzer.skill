"""
signals.py — Signal extraction from HTML (UX, persona-enhanced, core signals, IP geo).
"""
import re
import json
import socket
import urllib.request
import urllib.parse

from .constants import (
    TLD_MAP, CURRENCY_MAP, CURRENCY_SYMBOLS, PHONE_PREFIXES,
    SOCIAL_MEDIA_DOMAINS, PAYMENT_METHODS, SPELLING_VARIANTS, MEASUREMENT_UNITS,
)
from .html_parsing import HAS_BS4, _extract_text_bs4, _extract_text_stdlib, _extract_charset_from_content_type

try:
    from bs4 import BeautifulSoup
except ImportError:
    pass


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

        vp = soup.find('meta', attrs={'name': 'viewport'})
        if vp:
            signals['viewport'] = vp.get('content')

        for inp in soup.find_all('input'):
            signals['inputs'].append({
                'type': inp.get('type'),
                'inputmode': inp.get('inputmode'),
                'autocomplete': inp.get('autocomplete'),
                'name': inp.get('name'),
            })

        for img in soup.find_all('img', limit=20):
            signals['images'].append({
                'alt': img.get('alt'),
                'loading': img.get('loading'),
                'width': img.get('width'),
                'height': img.get('height'),
            })

        for link in soup.find_all('link'):
            rel = link.get('rel')
            if rel and ('preconnect' in rel or 'dns-prefetch' in rel):
                signals['links'].append({
                    'rel': rel,
                    'href': link.get('href'),
                })

    else:
        vp_match = re.search(r'<meta[^>]+name=["\']viewport["\'][^>]+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
        if vp_match:
            signals['viewport'] = vp_match.group(1)

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

        count = 0
        for m in re.finditer(r'<img([^>]+)>', html, re.IGNORECASE):
            if count >= 20:
                break
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
    """Extract persona-focused enhanced signals based on focus areas."""
    enhanced = {}

    if persona_focus.get('price_sensitive'):
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
            pricing_info[key] = bool(re.search(pattern, html, re.IGNORECASE))
        enhanced['pricing'] = pricing_info

        value_keywords = ['value', 'save', 'deal', 'bundle', 'pack', 'combo', 'best value']
        enhanced['value_proposition'] = any(kw in text_content.lower() for kw in value_keywords)

    if persona_focus.get('mobile_first'):
        viewport = re.search(r'<meta[^>]*name=["\']viewport["\']([^"\']*)', html, re.IGNORECASE)
        enhanced['viewport_configured'] = bool(viewport)

        if viewport:
            vp_content = viewport.group(1).lower()
            enhanced['viewport_mobile_optimized'] = all([
                'width=device-width' in vp_content,
                'initial-scale=1' in vp_content,
            ])

        enhanced['has_touch_elements'] = bool(re.search(
            r'(<button|<a[^>]*href)', html, re.IGNORECASE
        ))

        mobile_classes = ['mobile-', 'touch-', 'responsive-', 'xs-', 'sm-']
        enhanced['has_mobile_classes'] = any(cls in html for cls in mobile_classes)

    if persona_focus.get('local_trust'):
        enhanced['has_local_reviews'] = bool(re.search(
            r'review|rating|testimonial|star|verified|badge',
            html, re.IGNORECASE
        ))

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

        local_keywords = ['canadian', 'canada', 'local', 'domestic']
        enhanced['has_local_content'] = any(kw in text_content.lower() for kw in local_keywords)

    return enhanced


def extract_signals(html, url):
    """Extract all signals from HTML content."""
    if HAS_BS4:
        lang, meta_tags, hreflangs, text_content = _extract_text_bs4(html)
    else:
        lang, meta_tags, hreflangs, text_content = _extract_text_stdlib(html)

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

    currency_codes = [
        code for code in CURRENCY_MAP
        if re.search(r'\b' + code + r'\b', text_content)
    ]
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

    payment_methods = []
    for region, methods in PAYMENT_METHODS.items():
        for method in methods:
            if re.search(r'\b' + re.escape(method) + r'\b', text_content, re.IGNORECASE):
                payment_methods.append({'method': method, 'region': region})

    spelling_counts = {'US': 0, 'UK': 0}
    for variant, patterns in SPELLING_VARIANTS.items():
        for pattern in patterns:
            if re.search(pattern, text_content, re.IGNORECASE):
                spelling_counts[variant] += 1

    unit_counts = {'Imperial': 0, 'Metric': 0}
    for system, patterns in MEASUREMENT_UNITS.items():
        for pattern in patterns:
            if re.search(pattern, text_content, re.IGNORECASE):
                unit_counts[system] += 1

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
        'enhanced': {},
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
