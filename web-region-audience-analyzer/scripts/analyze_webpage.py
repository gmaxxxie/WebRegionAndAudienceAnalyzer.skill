#!/usr/bin/env python3
"""
Web Region & Audience Analyzer — backward-compatible shim.

All logic lives in the analyzer/ package.
This file exists so that:
  1. `python3 analyze_webpage.py <url>` still works as a CLI
  2. Scripts using `importlib.util.spec_from_file_location("analyze_webpage", path)`
     still get all the original public names.
"""
import os
import sys

# Ensure the scripts/ directory (parent of analyzer/) is on sys.path
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

# Re-export everything from the package
from analyzer import *  # noqa: F401, F403
from analyzer import (  # noqa: F401 — explicit so IDEs can resolve
    # constants
    TLD_MAP, LANG_TO_REGION, COUNTRY_NAMES, LANG_NAMES,
    PHONE_PREFIXES, PAYMENT_METHODS, SPELLING_VARIANTS, MEASUREMENT_UNITS,
    PAYMENT_METHODS, SPELLING_VARIANTS, MEASUREMENT_UNITS,
    # html_parsing
    SimpleHTMLParser, HAS_BS4,
    # fetcher
    fetch_html,
    # signals
    extract_signals, extract_persona_enhanced_signals, get_ip_geo,
    # language
    detect_language_nlpcloud, detect_language_offline, HAS_LANGDETECT,
    # scoring
    compute_result,
    # recommendations
    generate_recommendations, MAJOR_MARKETS, REGION_CURRENCY, REGION_SOCIAL,
    # crawling
    crawl_site, crawl_site_smart, extract_links, extract_links_with_metadata,
    extract_navigation_links, discover_sitemap, select_pages_heuristically,
    analyze_site_structure_with_ai, _normalize_url, _get_domain,
    # ai_analysis
    _call_ai_api, analyze_content_with_ai, AI_CONTENT_ANALYSIS_PROMPT,
    # persona
    resolve_target_audience, build_fallback_persona_analysis,
    compose_persona_analysis, create_persona_context,
    # aggregation
    aggregate_site_results, aggregate_site_optimization,
    aggregate_ai_analysis, aggregate_persona_analysis,
    # core
    analyze_site, analyze,
    # cli
    main,
)

# Also try to import export_utils for the markdown output path helper
try:
    from export_utils import build_default_markdown_output_path  # noqa: F401
except ImportError:
    build_default_markdown_output_path = None

if __name__ == '__main__':
    main()
