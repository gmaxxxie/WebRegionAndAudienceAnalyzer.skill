# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Web Region & Audience Analyzer — A multi-signal fusion tool for analyzing web pages to determine their geographic region, target audience, and primary language. Designed for cross-border multilingual websites (e.g., Shopify global stores, SaaS multi-language sites), not domestic single-language sites.

## Commands

### Single Page Analysis

```bash
# Analyze a single webpage with all features enabled (recommended)
python3 web-region-audience-analyzer/scripts/analyze_webpage.py https://example.com

# Save output to file
python3 web-region-audience-analyzer/scripts/analyze_webpage.py https://example.com -o result.json

# Disable IP geolocation (content signals only)
python3 web-region-audience-analyzer/scripts/analyze_webpage.py https://example.com --no-ip-geo

# Disable optimization recommendations
python3 web-region-audience-analyzer/scripts/analyze_webpage.py https://example.com --no-recommendations

# Use NLP Cloud for enhanced language detection
python3 web-region-audience-analyzer/scripts/analyze_webpage.py https://example.com --nlpcloud-token YOUR_TOKEN

# Custom timeout
python3 web-region-audience-analyzer/scripts/analyze_webpage.py https://example.com --timeout 30
```

### Multi-Page Site Crawling

```bash
# Crawl and analyze entire site (max 3 levels, 20 pages)
python3 web-region-audience-analyzer/scripts/analyze_webpage.py https://example.com --crawl

# Custom crawl parameters
python3 web-region-audience-analyzer/scripts/analyze_webpage.py https://example.com --crawl \
  --max-depth 2 --max-pages 10

# Crawl with output to file
python3 web-region-audience-analyzer/scripts/analyze_webpage.py https://example.com --crawl -o site_analysis.json
```

### AI Content Analysis

```bash
# Single page with AI content analysis
python3 web-region-audience-analyzer/scripts/analyze_webpage.py https://example.com \
  --ai-api-base https://api.openai.com/v1 \
  --ai-api-key YOUR_API_KEY

# Multi-page crawl with AI analysis (recommended)
python3 web-region-audience-analyzer/scripts/analyze_webpage.py https://example.com --crawl \
  --ai-api-base https://api.openai.com/v1 \
  --ai-api-key YOUR_API_KEY \
  --ai-model gpt-4o

# Use environment variables for API credentials
export AI_API_BASE=https://api.openai.com/v1
export AI_API_KEY=sk-your-key-here
python3 web-region-audience-analyzer/scripts/analyze_webpage.py https://example.com --crawl
```

### Dependencies

```bash
# Optional but recommended for best results
pip install beautifulsoup4 langdetect

# The script runs in degraded mode without these packages
```

## Architecture

### Analysis Modes

The analyzer supports two modes:

1. **Single Page Mode** (`analyze()` function, line 1868): Analyzes a single URL
2. **Site Crawl Mode** (`analyze_site()` function, line 1731): Crawls and analyzes multiple pages from a domain

### Multi-Signal Fusion Pipeline (Single Page)

The analyzer follows a 7-stage pipeline in the `analyze()` function (line 1868):

1. **Fetch HTML** — Dual-strategy SSL (standard → permissive fallback) to handle certificate issues
2. **Extract Signals** — Parse HTML for metadata, content patterns, and UX signals
3. **IP Geolocation** — Query ip-api.com for server location (CDN-aware)
4. **Language Detection** — NLP Cloud API (preferred) or langdetect (offline fallback)
5. **Compute Result** — Weighted scoring fusion across all signals
6. **Generate Recommendations** — Cross-border localization audit with A-F grading
7. **AI Content Analysis** — Optional LLM-based content analysis (if API credentials provided)

### Site Crawling Pipeline

The `analyze_site()` function (line 1731) implements multi-page analysis:

1. **Crawl** — BFS traversal up to max_depth (default 3) and max_pages (default 20)
   - Uses `crawl_site()` function (line 1355)
   - Extracts links with `extract_links()` (line 1306)
   - Only follows same-domain links
   - 1-second delay between requests

2. **Analyze Each Page** — Run full analysis pipeline on each crawled page
   - Shares IP geolocation across all pages (same domain)
   - Individual signal extraction and language detection per page
   - Per-page optimization recommendations

3. **Aggregate Results** — Combine results across all pages
   - `aggregate_site_results()` (line 1532): Weighted average of region/language signals
   - `aggregate_site_optimization()` (line 1608): Merge optimization issues
   - `aggregate_ai_analysis()` (line 1659): Average AI scores + combined suggestions

### AI Content Analysis

The `analyze_content_with_ai()` function (line 1483) uses an LLM to evaluate:

1. **Language Quality** (1-10 score)
   - Native level assessment
   - Machine translation detection
   - Grammar, naturalness, vocabulary appropriateness

2. **Region Fit** (1-10 score)
   - Cultural appropriateness
   - Specific issues (e.g., "Uses US date format for German audience")
   - Strengths (e.g., "Uses local currency correctly")

3. **Content-Product Alignment** (1-10 score)
   - Does copy/tone/messaging match the product?
   - Is value proposition clear for target audience?

4. **Actionable Suggestions**
   - Specific recommendations for improving localization quality

**API Compatibility**: Works with any OpenAI-compatible API (OpenAI, Azure OpenAI, Claude via proxy, etc.)

**Prompt**: See `AI_CONTENT_ANALYSIS_PROMPT` at line 1430

### Signal Sources & Weights

The `compute_result()` function (line 548) implements weighted scoring:

| Signal | Weight | Source |
|--------|--------|--------|
| TLD (`.de`, `.jp`) | 1.0 | Strong explicit signal |
| `<html lang="xx-YY">` with region | 0.9 | Explicit declaration |
| `<html lang="xx">` bare code | 0.7 | Inferred via `LANG_TO_REGION` map |
| `og:locale` | 0.8 | OpenGraph metadata |
| `content-language` | 0.7 | HTTP-equiv meta |
| Language detection | 0.6 × confidence | Statistical NLP |
| IP geolocation | 0.4 (0.2 if CDN) | Physical location |
| Currency codes | 0.3 each | Content pattern |
| Phone prefixes | 0.3 each | Content pattern |
| Social media | 0.3 each | Regional platforms |

**Key Insight**: Scores are accumulated per region, then normalized by `max_weight` to produce 0.0–1.0 confidence. CDN detection (Cloudflare, Akamai, Fastly) automatically reduces IP weight from 0.4 to 0.2.

### Key Functions

**Single Page Analysis:**
- **`analyze(url, ...)`** (line 1868) — Main entry point for single page analysis
- **`extract_signals(html, url)`** (line 400) — Parses HTML for all signal types, returns `(signals_dict, text_content)`
- **`compute_result(evidence)`** (line 548) — Core fusion algorithm, returns `{primaryRegion, primaryLanguage, confidence, ...}`
- **`generate_recommendations(evidence, result)`** (line 750) — Audits 8 categories (hreflang, locale, market adaptation, UX, etc.), returns grade + actionable fixes
- **`fetch_html(url, timeout)`** (line 271) — Dual SSL strategy with redirect following

**Multi-Page Crawling:**
- **`analyze_site(url, max_depth, max_pages, ...)`** (line 1731) — Main entry point for site crawling mode
- **`crawl_site(start_url, max_depth, max_pages, ...)`** (line 1355) — BFS crawler, returns list of `{url, html, depth, final_url}`
- **`extract_links(html, base_url)`** (line 1306) — Extracts all `<a href>` links from HTML, resolves relative URLs
- **`aggregate_site_results(page_results)`** (line 1532) — Combines region/language signals across all pages
- **`aggregate_site_optimization(page_results)`** (line 1608) — Merges optimization issues from all pages
- **`aggregate_ai_analysis(page_ai_results)`** (line 1659) — Averages AI scores and combines suggestions

**AI Content Analysis:**
- **`analyze_content_with_ai(text_content, url, result, ...)`** (line 1483) — Calls LLM API to analyze content quality
- **`_call_ai_api(messages, api_base, api_key, ...)`** (line 1403) — Generic OpenAI-compatible API caller

**Text Extraction:**
- **`_extract_text_bs4(html)`** (line 205) — BeautifulSoup-based extraction (preferred)
- **`_extract_text_stdlib(html)`** (line 254) — Stdlib fallback using HTMLParser

### Text Extraction Strategy

For JavaScript-heavy pages (common in CJK sites), the analyzer uses a fallback strategy:
1. Try BeautifulSoup with comment/script/style removal
2. If insufficient text, extract `<title>` + `<meta name="description">` as last resort
3. This prevents "insufficient text" errors on JS-rendered pages

### CDN Detection

The `get_ip_geo()` function (line 495) checks ISP/Org fields against known CDN providers:
- Cloudflare, Akamai, Fastly, Amazon CloudFront, Google Cloud CDN, Azure CDN, etc.
- When detected, IP signal weight drops from 0.4 to 0.2 to avoid false positives

### Optimization Recommendations

The `generate_recommendations()` function audits 8 categories with severity levels:

| Category | Severity | What It Checks |
|----------|----------|----------------|
| `hreflang` | Critical | Missing tags, no x-default, no self-reference |
| `locale-declaration` | Critical | Missing `<html lang>`, `og:locale`, `content-language` |
| `locale-consistency` | Warning | Conflicts between declared signals |
| `tld-content-mismatch` | Warning | ccTLD region vs content language mismatch |
| `market-adaptation` | Warning | Local currency, phone formats, social media, **payment methods** |
| `cultural-adaptation` | Info | Spelling (US vs UK), measurement units (metric vs imperial) |
| `ux-mobile` | Critical | Viewport meta tag |
| `ux-forms` | Warning | Input types (email, tel) |
| `accessibility` | Info | Image alt text |
| `hosting-alignment` | Info | Server location vs target audience |
| `charset` | Warning | UTF-8 for multilingual content |

**Grading**: A (80-100), B (60-79), C (40-59), D (20-39), F (0-19)

## Important Constants

### Mappings (lines 40-100)

- **`TLD_MAP`** — 50+ ccTLD to country code mappings
- **`LANG_TO_REGION`** — Bare language codes to primary country (e.g., `ja` → `JP`, `de` → `DE`)
  - Note: English intentionally excluded (too global)
- **`COUNTRY_NAMES`** — ISO codes to human-readable names
- **`LANG_NAMES`** — Language codes to names
- **`PHONE_PREFIXES`** — Regex patterns for international phone formats
- **`CURRENCY_CODES`** — 3-letter codes (USD, EUR, JPY, etc.)
- **`SOCIAL_MEDIA_REGIONS`** — Regional platforms (WeChat→CN, VK→RU, LINE→JP, etc.)

### Payment Methods (line ~1100)

The analyzer checks for regional payment methods in content:
- Germany: Sofort, Klarna
- Netherlands: iDEAL
- Brazil: Pix, Boleto
- India: UPI, Paytm
- China: Alipay, WeChat Pay
- Japan: Konbini, PayPay
- And more...

## Output Format

### Single Page Mode

The analyzer returns a JSON object with:

```json
{
  "url": "...",
  "mode": "page",
  "analyzedAt": "ISO 8601 timestamp",
  "result": {
    "primaryRegion": "ISO 3166-1 alpha-2",
    "primaryRegionName": "Human-readable",
    "primaryLanguage": "ISO 639-1",
    "primaryLanguageName": "Human-readable",
    "likelyAudience": "Descriptive string",
    "regionConfidence": 0.0-1.0,
    "languageConfidence": 0.0-1.0,
    "signalBreakdown": {"US": 2.4, "GB": 0.3}
  },
  "evidence": {
    "htmlSignals": {...},
    "contentSignals": {...},
    "ipGeolocation": {...},
    "languageDetection": {...}
  },
  "optimization": {
    "summary": {"score": 0-100, "grade": "A-F", ...},
    "recommendations": [...]
  },
  "aiContentAnalysis": {
    "inferredProductType": "...",
    "languageQuality": {"score": 1-10, "isNativeLevel": true/false, ...},
    "regionFit": {"score": 1-10, "culturallyApproriate": true/false, ...},
    "contentProductAlignment": {"score": 1-10, ...},
    "suggestions": [...]
  },
  "errors": [],
  "warnings": []
}
```

### Site Crawl Mode

When using `--crawl`, the output structure changes:

```json
{
  "url": "...",
  "mode": "site",
  "analyzedAt": "ISO 8601 timestamp",
  "crawlSummary": {
    "pagesAnalyzed": 15,
    "maxDepthReached": 2,
    "pageUrls": ["...", "..."]
  },
  "siteResult": {
    "primaryRegion": "...",
    "regionConfidence": 0.0-1.0,
    // Aggregated across all pages
  },
  "siteOptimization": {
    "summary": {"score": 0-100, "grade": "A-F", ...},
    "recommendations": [...]
    // Merged from all pages
  },
  "aiContentAnalysis": {
    "averageLanguageQuality": 8.5,
    "averageRegionFit": 9.0,
    "averageContentAlignment": 8.0,
    "aggregatedSuggestions": [...]
    // Averaged and combined from all pages
  },
  "pages": [
    {
      "url": "...",
      "depth": 0,
      "result": {...},
      "evidence": {...},
      "optimization": {...},
      "aiContentAnalysis": {...}
    },
    // ... one entry per crawled page
  ],
  "errors": [],
  "warnings": []
}
```

## API Rate Limits

- **ip-api.com**: 45 requests/minute (free tier, HTTP only)
- **NLP Cloud**: Depends on your plan (optional, for enhanced language detection)

## Known Limitations

- **JavaScript Rendering**: Does not execute JS, so SPA sites may have insufficient text
- **CDN Masking**: IP geolocation less reliable for CDN-hosted sites (mitigated by weight reduction)
- **Multilingual Pages**: Takes highest-confidence language, doesn't aggregate multi-language weights
- **Global Sites**: `.com` + English + US CDN = low confidence (this is correct behavior)

## File Structure

```
web-region-audience-analyzer/
├── scripts/
│   └── analyze_webpage.py       # Main script (2018 lines, self-contained)
├── references/
│   ├── api-reference.md         # IP-API & NLP Cloud docs
│   └── signal-patterns.md       # Regex patterns & mappings
└── SKILL.md                     # Skill metadata for Claude Code
```

## Development Notes

- The script is designed to be **zero-dependency** (runs with stdlib only), but `beautifulsoup4` and `langdetect` significantly improve results
- All subsystems are **fault-tolerant** — if one signal source fails, others continue and errors are logged to `errors`/`warnings`
- The script uses **dual SSL strategy** — tries standard SSL first, falls back to permissive context if certificate validation fails
- **CJK optimization** — For JS-heavy pages, falls back to extracting `<title>` + `<meta description>` to ensure some text is available for language detection
