"""
Cross-border localization optimization recommendations.
"""
from .constants import TLD_MAP, LANG_TO_REGION, LANG_NAMES, COUNTRY_NAMES, PAYMENT_METHODS

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
             break  # Only report once

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
             break  # Only report once

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
