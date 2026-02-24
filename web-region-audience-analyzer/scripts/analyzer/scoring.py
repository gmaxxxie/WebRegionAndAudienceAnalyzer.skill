"""
scoring.py — Multi-signal fusion and weighted scoring (compute_result).
"""
import re

from .constants import TLD_MAP, LANG_TO_REGION, COUNTRY_NAMES, LANG_NAMES


def compute_result(evidence):
    """
    Multi-signal fusion with weighted scoring.

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

    # --- Language detection results contribute to scoring ---
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
    from .constants import CURRENCY_MAP
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
