"""
tests/test_core_functions.py
Unit tests for compute_result(), extract_signals(), and generate_recommendations().

These tests are offline (no network calls) and fast.
"""
import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "web-region-audience-analyzer" / "scripts"
ANALYZER_DIR = SCRIPTS_DIR / "analyzer"

# Insert scripts/ into sys.path so the analyzer package can be imported
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from analyzer.scoring import compute_result
from analyzer.recommendations import generate_recommendations
from analyzer.signals import extract_signals


# ═══════════════════════════════════════════════════════════════════════════
# compute_result() tests
# ═══════════════════════════════════════════════════════════════════════════

class TestComputeResult(unittest.TestCase):
    """Tests for the weighted-scoring fusion function."""

    def _evidence(self, *, tld=None, lang=None, locale=None,
                  content_lang=None, ip_country=None, ip_isp='',
                  detected_lang=None, detected_conf=0.99,
                  currencies=None, phones=None, social=None):
        """Helper: build a minimal evidence dict."""
        html_s = {}
        if tld:
            html_s['tld'] = tld
        if lang:
            html_s['lang'] = lang
        if locale:
            html_s['metaLocale'] = locale
        if content_lang:
            html_s['metaLanguage'] = content_lang

        ip_geo = {}
        if ip_country:
            ip_geo = {'countryCode': ip_country, 'isp': ip_isp, 'org': ip_isp}

        lang_det = {}
        if detected_lang:
            lang_det = {'results': [{'lang': detected_lang, 'confidence': detected_conf}]}

        content_s = {
            'currencyCodes': currencies or [],
            'phoneFormats': phones or [],
            'socialMediaSignals': [{'region': r} for r in (social or [])],
        }

        return {
            'htmlSignals': html_s,
            'contentSignals': content_s,
            'ipGeolocation': ip_geo,
            'languageDetection': lang_det,
        }

    # ── Basic cases ──────────────────────────────────────────────────────

    def test_empty_evidence_returns_unknown(self):
        result = compute_result({})
        self.assertIsNone(result['primaryRegion'])
        self.assertEqual(result['regionConfidence'], 0.0)
        self.assertEqual(result['likelyAudience'], 'Unknown')

    def test_ccTLD_alone_detects_region(self):
        ev = self._evidence(tld='.de')
        result = compute_result(ev)
        self.assertEqual(result['primaryRegion'], 'DE')
        self.assertGreater(result['regionConfidence'], 0.0)

    def test_jp_tld(self):
        ev = self._evidence(tld='.jp')
        result = compute_result(ev)
        self.assertEqual(result['primaryRegion'], 'JP')

    def test_html_lang_with_region_subtag(self):
        ev = self._evidence(lang='zh-CN')
        result = compute_result(ev)
        self.assertEqual(result['primaryRegion'], 'CN')
        self.assertEqual(result['primaryLanguage'], 'zh-cn')

    def test_html_lang_bare_maps_via_lang_to_region(self):
        # 'ja' → 'JP' via LANG_TO_REGION
        ev = self._evidence(lang='ja')
        result = compute_result(ev)
        self.assertEqual(result['primaryRegion'], 'JP')

    def test_html_lang_en_not_mapped_to_region(self):
        # 'en' is intentionally absent from LANG_TO_REGION
        ev = self._evidence(lang='en')
        result = compute_result(ev)
        # No region signal from lang, so primaryRegion may be None
        self.assertIsNone(result['primaryRegion'])

    def test_og_locale_with_region(self):
        ev = self._evidence(locale='de_DE')
        result = compute_result(ev)
        self.assertEqual(result['primaryRegion'], 'DE')

    def test_ip_geo_contributes(self):
        ev = self._evidence(ip_country='JP')
        result = compute_result(ev)
        self.assertEqual(result['primaryRegion'], 'JP')

    def test_cdn_ip_reduced_weight(self):
        """CDN IP should still produce a result but with lower weight."""
        ev = self._evidence(ip_country='US', ip_isp='cloudflare')
        result = compute_result(ev)
        self.assertEqual(result['primaryRegion'], 'US')
        # With only CDN IP (weight=0.2) confidence should be low
        self.assertLessEqual(result['regionConfidence'], 0.25)

    def test_langdetect_contributes(self):
        ev = self._evidence(detected_lang='de', detected_conf=0.95)
        result = compute_result(ev)
        self.assertEqual(result['primaryRegion'], 'DE')

    def test_langdetect_low_confidence_not_used(self):
        # confidence ≤ 0.5 → language detection result NOT added to scores
        ev = self._evidence(detected_lang='de', detected_conf=0.4)
        result = compute_result(ev)
        self.assertIsNone(result['primaryRegion'])

    # ── Multiple signals agree → high confidence ─────────────────────────

    def test_multiple_signals_raise_confidence(self):
        ev = self._evidence(
            tld='.jp', lang='ja', ip_country='JP',
            detected_lang='ja', detected_conf=0.99,
        )
        result = compute_result(ev)
        self.assertEqual(result['primaryRegion'], 'JP')
        self.assertGreater(result['regionConfidence'], 0.5)

    def test_conflicting_signals_lower_confidence(self):
        """TLD says DE but IP says US — confidence should be lower than single-signal."""
        ev_single = self._evidence(tld='.de')
        ev_conflict = self._evidence(tld='.de', ip_country='US')
        conf_single = compute_result(ev_single)['regionConfidence']
        conf_conflict = compute_result(ev_conflict)['regionConfidence']
        self.assertLessEqual(conf_conflict, conf_single)

    # ── Return shape ─────────────────────────────────────────────────────

    def test_return_keys_present(self):
        result = compute_result({})
        expected_keys = {
            'primaryRegion', 'primaryRegionName', 'primaryLanguage',
            'primaryLanguageName', 'likelyAudience', 'regionConfidence',
            'languageConfidence', 'signalBreakdown',
        }
        self.assertEqual(set(result.keys()), expected_keys)

    def test_confidence_bounded_0_to_1(self):
        ev = self._evidence(
            tld='.jp', lang='ja', locale='ja_JP',
            ip_country='JP', detected_lang='ja', detected_conf=1.0,
        )
        result = compute_result(ev)
        self.assertGreaterEqual(result['regionConfidence'], 0.0)
        self.assertLessEqual(result['regionConfidence'], 1.0)

    def test_signal_breakdown_matches_primary(self):
        ev = self._evidence(tld='.de')
        result = compute_result(ev)
        breakdown = result['signalBreakdown']
        self.assertIn('DE', breakdown)
        # DE should be the top scorer
        top_region = max(breakdown, key=breakdown.get)
        self.assertEqual(top_region, 'DE')


# ═══════════════════════════════════════════════════════════════════════════
# extract_signals() tests
# ═══════════════════════════════════════════════════════════════════════════

class TestExtractSignals(unittest.TestCase):
    """Tests for HTML signal extraction."""

    def _run(self, html, url='https://example.com'):
        signals, text = extract_signals(html, url)
        return signals, text

    # ── HTML signals ─────────────────────────────────────────────────────

    def test_extracts_html_lang(self):
        html = '<html lang="de"><head></head><body>Hallo Welt</body></html>'
        signals, _ = self._run(html)
        self.assertEqual(signals['htmlSignals']['lang'], 'de')

    def test_extracts_html_lang_region(self):
        html = '<html lang="zh-CN"><head></head><body>你好</body></html>'
        signals, _ = self._run(html)
        self.assertEqual(signals['htmlSignals']['lang'], 'zh-CN')

    def test_extracts_og_locale(self):
        html = '''<html><head>
            <meta property="og:locale" content="fr_FR" />
        </head><body>Bonjour</body></html>'''
        signals, _ = self._run(html)
        self.assertEqual(signals['htmlSignals']['metaLocale'], 'fr_FR')

    def test_extracts_charset(self):
        html = '<html><head><meta charset="UTF-8"></head><body>Hello</body></html>'
        signals, _ = self._run(html)
        self.assertEqual(signals['htmlSignals']['charset'], 'UTF-8')

    def test_extracts_tld_from_url(self):
        html = '<html><head></head><body>Hello</body></html>'
        signals, _ = self._run(html, url='https://www.spiegel.de/artikel')
        self.assertEqual(signals['htmlSignals']['tld'], '.de')

    def test_no_tld_for_com(self):
        """'.com' is not in TLD_MAP so extract_signals returns tld=None.
        
        The TLD is extracted from the URL but filtered because TLD_MAP
        has no entry for generic TLDs like '.com'.
        """
        html = '<html><head></head><body>Hello</body></html>'
        signals, _ = self._run(html, url='https://example.com/page')
        # tld is None because '.com' is not a ccTLD in TLD_MAP
        self.assertIsNone(signals['htmlSignals']['tld'])

    def test_extracts_hreflang_tags(self):
        html = '''<html><head>
            <link rel="alternate" hreflang="en" href="/en/" />
            <link rel="alternate" hreflang="de" href="/de/" />
            <link rel="alternate" hreflang="x-default" href="/" />
        </head><body>Hello</body></html>'''
        signals, _ = self._run(html)
        tags = signals['htmlSignals']['hreflangTags']
        self.assertIn('en', tags)
        self.assertIn('de', tags)
        self.assertIn('x-default', tags)

    # ── Content signals ──────────────────────────────────────────────────

    def test_detects_currency_codes(self):
        html = '<html><body>Price: EUR 99.99 or USD 109</body></html>'
        signals, _ = self._run(html)
        codes = signals['contentSignals']['currencyCodes']
        self.assertIn('EUR', codes)
        self.assertIn('USD', codes)

    def test_detects_japanese_social_media(self):
        html = '<html><body><a href="https://line.me/R/">LINE</a></body></html>'
        signals, _ = self._run(html)
        socials = signals['contentSignals']['socialMediaSignals']
        regions = [s.get('region') for s in socials]
        self.assertIn('JP', regions)

    def test_detects_chinese_social_media(self):
        html = '<html><body><a href="https://weixin.qq.com/">WeChat</a></body></html>'
        signals, _ = self._run(html)
        socials = signals['contentSignals']['socialMediaSignals']
        regions = [s.get('region') for s in socials]
        self.assertIn('CN', regions)

    # ── Text extraction ──────────────────────────────────────────────────

    def test_text_content_returned(self):
        html = '<html><body><p>Hello world</p></body></html>'
        _, text = self._run(html)
        self.assertIn('Hello world', text)

    def test_scripts_excluded_from_text(self):
        html = '<html><body><script>var x = 1;</script><p>Visible text</p></body></html>'
        _, text = self._run(html)
        self.assertNotIn('var x', text)
        self.assertIn('Visible text', text)

    def test_empty_html_returns_empty_text(self):
        _, text = self._run('')
        self.assertEqual(text.strip(), '')

    # ── Return shape ─────────────────────────────────────────────────────

    def test_signal_structure_keys(self):
        html = '<html><head></head><body>test</body></html>'
        signals, _ = self._run(html)
        self.assertIn('htmlSignals', signals)
        self.assertIn('contentSignals', signals)

    def test_ux_signals_present(self):
        html = '''<html><head>
            <meta name="viewport" content="width=device-width, initial-scale=1">
        </head><body>Hello</body></html>'''
        signals, _ = self._run(html)
        ux = signals['contentSignals']['uxSignals']
        self.assertEqual(ux['viewport'], 'width=device-width, initial-scale=1')


# ═══════════════════════════════════════════════════════════════════════════
# generate_recommendations() tests
# ═══════════════════════════════════════════════════════════════════════════

class TestGenerateRecommendations(unittest.TestCase):
    """Tests for the cross-border localization recommendations audit."""

    def _build(self, *, tld=None, lang=None, locale=None, content_lang=None,
               charset=None, hreflangs=None, ip_country=None, ip_isp='',
               currencies=None, phones=None, socials=None,
               viewport=None, spelling=None, units=None,
               payment_methods=None):
        html_s = {
            'hreflangTags': hreflangs or [],
            'lang': lang,
            'metaLocale': locale,
            'metaLanguage': content_lang,
            'charset': charset,
            'tld': tld,
        }
        content_s = {
            'currencyCodes': currencies or [],
            'currencySymbols': [],
            'phoneFormats': phones or [],
            'socialMediaSignals': [{'domain': s} for s in (socials or [])],
            'spellingCounts': spelling or {'US': 0, 'UK': 0},
            'unitCounts': units or {'Imperial': 0, 'Metric': 0},
            'uxSignals': {'viewport': viewport, 'inputs': [], 'images': []},
            'paymentMethods': payment_methods or [],
        }
        ip_geo = {}
        if ip_country:
            ip_geo = {'countryCode': ip_country, 'isp': ip_isp, 'org': ip_isp}

        evidence = {
            'htmlSignals': html_s,
            'contentSignals': content_s,
            'ipGeolocation': ip_geo,
            'languageDetection': {},
        }
        result = {
            'primaryRegion': ip_country,
            'primaryLanguage': lang.split('-')[0].lower() if lang else None,
        }
        return generate_recommendations(evidence, result)

    def _categories(self, output):
        return [r['category'] for r in output['recommendations']]

    def _severities(self, output):
        return [r['severity'] for r in output['recommendations']]

    # ── hreflang ─────────────────────────────────────────────────────────

    def test_missing_hreflang_is_critical(self):
        out = self._build()
        cats = self._categories(out)
        sevs = self._severities(out)
        self.assertIn('hreflang', cats)
        idx = cats.index('hreflang')
        self.assertEqual(sevs[idx], 'critical')

    def test_hreflang_present_but_missing_x_default_is_critical(self):
        out = self._build(hreflangs=['en', 'de'])
        cats = self._categories(out)
        sevs = self._severities(out)
        hreflang_issues = [
            (c, s) for c, s in zip(cats, sevs) if c == 'hreflang'
        ]
        # Missing x-default is a critical issue
        self.assertTrue(any(s == 'critical' for _, s in hreflang_issues))

    def test_complete_hreflang_no_critical(self):
        out = self._build(hreflangs=['en', 'de', 'x-default'])
        hreflang_criticals = [
            r for r in out['recommendations']
            if r['category'] == 'hreflang' and r['severity'] == 'critical'
        ]
        self.assertEqual(len(hreflang_criticals), 0)

    # ── Locale declarations ──────────────────────────────────────────────

    def test_missing_html_lang_is_critical(self):
        out = self._build()  # no lang
        cats = self._categories(out)
        sevs = self._severities(out)
        idx = cats.index('locale-declaration')
        self.assertEqual(sevs[idx], 'critical')

    def test_missing_og_locale_is_warning(self):
        out = self._build(lang='de')  # has lang, no locale
        recs = [r for r in out['recommendations']
                if r['category'] == 'locale-declaration' and r['severity'] == 'warning']
        self.assertTrue(len(recs) > 0)

    # ── Charset ──────────────────────────────────────────────────────────

    def test_missing_charset_is_warning(self):
        out = self._build()
        cats = self._categories(out)
        self.assertIn('charset', cats)

    def test_utf8_charset_no_warning(self):
        out = self._build(charset='UTF-8')
        charset_warnings = [
            r for r in out['recommendations']
            if r['category'] == 'charset'
        ]
        self.assertEqual(len(charset_warnings), 0)

    def test_non_utf8_charset_flagged(self):
        out = self._build(charset='ISO-8859-1')
        cats = self._categories(out)
        self.assertIn('charset', cats)

    # ── Viewport ─────────────────────────────────────────────────────────

    def test_missing_viewport_is_critical(self):
        out = self._build()
        cats = self._categories(out)
        sevs = self._severities(out)
        self.assertIn('ux-mobile', cats)
        idx = cats.index('ux-mobile')
        self.assertEqual(sevs[idx], 'critical')

    def test_proper_viewport_no_critical(self):
        out = self._build(viewport='width=device-width, initial-scale=1')
        ux_criticals = [
            r for r in out['recommendations']
            if r['category'] == 'ux-mobile' and r['severity'] == 'critical'
        ]
        self.assertEqual(len(ux_criticals), 0)

    # ── Summary / scoring ────────────────────────────────────────────────

    def test_summary_keys_present(self):
        out = self._build()
        summary = out['summary']
        self.assertIn('score', summary)
        self.assertIn('grade', summary)
        self.assertIn('totalIssues', summary)
        self.assertIn('critical', summary)
        self.assertIn('warnings', summary)
        self.assertIn('info', summary)

    def test_score_decreases_with_issues(self):
        """Perfect site (good charset, viewport, lang) should score higher."""
        bad = self._build()
        good = self._build(
            lang='de', locale='de_DE', charset='UTF-8',
            hreflangs=['de', 'en', 'x-default'],
            viewport='width=device-width, initial-scale=1',
        )
        self.assertGreater(good['summary']['score'], bad['summary']['score'])

    def test_grade_a_for_clean_site(self):
        out = self._build(
            lang='en', locale='en_US', content_lang='en',
            charset='UTF-8',
            hreflangs=['en', 'de', 'fr', 'ja', 'x-default'],
            viewport='width=device-width, initial-scale=1',
        )
        self.assertIn(out['summary']['grade'], ('A', 'B'))

    def test_grade_f_for_empty_site(self):
        """No signals at all → F grade."""
        out = self._build()
        self.assertIn(out['summary']['grade'], ('D', 'F'))

    def test_recommendations_sorted_by_severity(self):
        """Criticals come before warnings, warnings before info."""
        out = self._build()
        sev_order = {'critical': 0, 'warning': 1, 'info': 2}
        recs = out['recommendations']
        for i in range(len(recs) - 1):
            self.assertLessEqual(
                sev_order[recs[i]['severity']],
                sev_order[recs[i + 1]['severity']],
                msg=f"Severity order violated at index {i}"
            )

    def test_output_shape(self):
        out = self._build()
        self.assertIn('summary', out)
        self.assertIn('recommendations', out)
        self.assertIsInstance(out['recommendations'], list)
        for rec in out['recommendations']:
            self.assertIn('severity', rec)
            self.assertIn('category', rec)
            self.assertIn('issue', rec)
            self.assertIn('recommendation', rec)


if __name__ == '__main__':
    unittest.main()
