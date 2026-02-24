"""
Core analysis entry points: analyze() and analyze_site().
"""
import sys
import urllib.parse
from datetime import datetime, timezone

from .fetcher import fetch_html
from .signals import extract_signals, extract_persona_enhanced_signals, get_ip_geo
from .language import detect_language_nlpcloud, detect_language_offline, HAS_LANGDETECT
from .scoring import compute_result
from .recommendations import generate_recommendations
from .crawling import crawl_site, crawl_site_smart
from .ai_analysis import analyze_content_with_ai
from .persona import resolve_target_audience, create_persona_context, compose_persona_analysis
from .aggregation import (
    aggregate_site_results, aggregate_site_optimization,
    aggregate_ai_analysis, aggregate_persona_analysis,
)


def analyze_site(url, max_depth=3, max_pages=20, include_ip_geo=True,
                 nlpcloud_token=None, timeout=15, include_recommendations=True,
                 ai_api_base=None, ai_api_key=None, ai_model='gpt-4o',
                 target_audience=None, use_smart_crawl=False):
    """
    Analyze a website.

    Args:
        use_smart_crawl: If True, use AI-driven smart crawling (analyze structure first,
                         then select important pages). Otherwise use traditional BFS crawl.
    """
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
                'primaryLanguage': 'en',
                'primaryLanguageName': 'English',
                'likelyAudience': 'Unknown audience',
            }

    target_audience_result = resolve_target_audience(target_audience, initial_result)
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

    site_map = None

    if use_smart_crawl:
        print(f"Smart crawling {url} (max_pages={max_pages})...", file=sys.stderr)
        crawl_result = crawl_site_smart(
            url, max_pages=max_pages, timeout=timeout, delay=1.0,
            progress_callback=_progress, use_ai=True,
            ai_api_base=ai_api_base, ai_api_key=ai_api_key, ai_model=ai_model
        )
        crawled = crawl_result['results']
        site_map = crawl_result['site_map']
    else:
        print(f"Crawling {url} (max_depth={max_depth}, max_pages={max_pages})...", file=sys.stderr)
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

    if site_map:
        output['crawlSummary']['siteMap'] = site_map

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

        # Extract persona-enhanced signals
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
            persona_context=persona_context,
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
                'primaryLanguage': 'en',
                'primaryLanguageName': 'English',
                'likelyAudience': 'Unknown audience',
            }

    target_audience_result = resolve_target_audience(target_audience, initial_result)
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

    # 2.5. Extract persona-enhanced signals
    persona_context = None
    if target_audience or include_ip_geo:
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

        target_audience_result = resolve_target_audience(target_audience, initial_result)
        persona_context = create_persona_context(target_audience_result)

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
