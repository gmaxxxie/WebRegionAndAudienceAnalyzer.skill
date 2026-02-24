"""
analyzer package — re-exports all public names for backward compatibility.
"""
from .constants import (
    TLD_MAP, LANG_TO_REGION, COUNTRY_NAMES, LANG_NAMES,
    PHONE_PREFIXES, PAYMENT_METHODS, SPELLING_VARIANTS, MEASUREMENT_UNITS,
    PAYMENT_METHODS, SPELLING_VARIANTS, MEASUREMENT_UNITS,
)
from .html_parsing import SimpleHTMLParser, HAS_BS4
from .fetcher import fetch_html
from .signals import extract_signals, extract_persona_enhanced_signals, get_ip_geo
from .language import detect_language_nlpcloud, detect_language_offline, HAS_LANGDETECT
from .scoring import compute_result
from .recommendations import (
    generate_recommendations, MAJOR_MARKETS, REGION_CURRENCY, REGION_SOCIAL,
)
from .crawling import (
    crawl_site, crawl_site_smart, extract_links, extract_links_with_metadata,
    extract_navigation_links, discover_sitemap, select_pages_heuristically,
    analyze_site_structure_with_ai, _normalize_url, _get_domain,
)
from .ai_analysis import _call_ai_api, analyze_content_with_ai, AI_CONTENT_ANALYSIS_PROMPT
from .persona import (
    resolve_target_audience, build_fallback_persona_analysis,
    compose_persona_analysis, create_persona_context,
)
from .aggregation import (
    aggregate_site_results, aggregate_site_optimization,
    aggregate_ai_analysis, aggregate_persona_analysis,
)
from .core import analyze_site, analyze
from .cli import main

__all__ = [
    # constants
    'TLD_MAP', 'LANG_TO_REGION', 'COUNTRY_NAMES', 'LANG_NAMES',
    'PHONE_PREFIXES', 'PAYMENT_METHODS', 'SPELLING_VARIANTS', 'MEASUREMENT_UNITS',
    'PAYMENT_METHODS', 'SPELLING_VARIANTS', 'MEASUREMENT_UNITS',
    # html_parsing
    'SimpleHTMLParser', 'HAS_BS4',
    # fetcher
    'fetch_html',
    # signals
    'extract_signals', 'extract_persona_enhanced_signals', 'get_ip_geo',
    # language
    'detect_language_nlpcloud', 'detect_language_offline', 'HAS_LANGDETECT',
    # scoring
    'compute_result',
    # recommendations
    'generate_recommendations', 'MAJOR_MARKETS', 'REGION_CURRENCY', 'REGION_SOCIAL',
    # crawling
    'crawl_site', 'crawl_site_smart', 'extract_links', 'extract_links_with_metadata',
    'extract_navigation_links', 'discover_sitemap', 'select_pages_heuristically',
    'analyze_site_structure_with_ai', '_normalize_url', '_get_domain',
    # ai_analysis
    '_call_ai_api', 'analyze_content_with_ai', 'AI_CONTENT_ANALYSIS_PROMPT',
    # persona
    'resolve_target_audience', 'build_fallback_persona_analysis',
    'compose_persona_analysis', 'create_persona_context',
    # aggregation
    'aggregate_site_results', 'aggregate_site_optimization',
    'aggregate_ai_analysis', 'aggregate_persona_analysis',
    # core
    'analyze_site', 'analyze',
    # cli
    'main',
]
