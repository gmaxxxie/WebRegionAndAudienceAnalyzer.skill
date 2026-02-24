"""
Multi-page crawling: BFS and smart (sitemap/navigation/AI) strategies.
"""
import json
import re
import sys
import time
import urllib.parse
from collections import deque

from .fetcher import fetch_html
from .html_parsing import HAS_BS4
from .ai_analysis import _call_ai_api

if HAS_BS4:
    from bs4 import BeautifulSoup


# ── Helpers ──────────────────────────────────────────────────────────────────

def _normalize_url(url):
    parsed = urllib.parse.urlparse(url)
    normalized = parsed._replace(fragment='')
    path = normalized.path.rstrip('/') or '/'
    normalized = normalized._replace(path=path)
    return urllib.parse.urlunparse(normalized)


def _get_domain(url):
    return urllib.parse.urlparse(url).netloc.lower()


# ── Basic link extraction ─────────────────────────────────────────────────────

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


def extract_links_with_metadata(html, base_url):
    """Extract links with text content and URL metadata for AI analysis."""
    base_domain = _get_domain(base_url)
    links = []

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
        for a in anchors:
            href = a['href'].strip()
            text = a.get_text(strip=True) or ''
            title = a.get('title', '') or ''

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
            links.append({
                'url': normalized,
                'text': text[:200],
                'title': title[:200],
                'path': parsed.path,
            })
    else:
        # Fallback: regex-based extraction
        raw_hrefs = re.findall(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>([^<]*)</a>', html, re.IGNORECASE)
        for href, text in raw_hrefs:
            href = href.strip()
            text = text.strip()[:200]

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
            links.append({
                'url': normalized,
                'text': text,
                'title': '',
                'path': parsed.path,
            })

    return links


def extract_navigation_links(html, base_url):
    """
    Extract links specifically from navigation areas (nav, header, menu).

    Returns: list of link dictionaries (same format as extract_links_with_metadata)
    """
    nav_links = []

    if HAS_BS4:
        soup = BeautifulSoup(html, 'html.parser')

        # Look for links in common navigation containers
        nav_selectors = [
            'nav a',
            '[role="navigation"] a',
            'header a',
            '.nav a',
            '.navigation a',
            '.menu a',
            '#nav a',
            '#menu a',
            '.navbar a',
            '.header a',
        ]

        SKIP_EXTENSIONS = {
            '.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp', '.ico', '.bmp',
            '.css', '.js', '.json', '.xml', '.rss', '.atom',
            '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
            '.zip', '.tar', '.gz', '.rar', '.7z',
            '.mp3', '.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm',
            '.woff', '.woff2', '.ttf', '.eot', '.otf',
        }

        for selector in nav_selectors:
            anchors = soup.select(selector)
            for a in anchors:
                href = a.get('href', '').strip()
                text = a.get_text(strip=True) or ''
                title = a.get('title', '') or ''

                if not href or href.startswith(('mailto:', 'tel:', 'javascript:', 'data:', '#', 'ftp:')):
                    continue

                try:
                    absolute = urllib.parse.urljoin(base_url, href)
                    parsed = urllib.parse.urlparse(absolute)

                    if parsed.scheme not in ('http', 'https'):
                        continue

                    path_lower = parsed.path.lower()
                    if any(path_lower.endswith(ext) for ext in SKIP_EXTENSIONS):
                        continue

                    normalized = _normalize_url(absolute)
                    nav_links.append({
                        'url': normalized,
                        'text': text[:200],
                        'title': title[:200],
                        'path': parsed.path,
                        'source': 'navigation',
                    })
                except Exception:
                    continue

            # If we found navigation links, don't try other selectors
            if nav_links:
                break

    return nav_links


# ── Heuristic & AI page selection ────────────────────────────────────────────

def select_pages_heuristically(links, max_pages=20):
    """Fallback heuristic-based page selection."""
    highest_priority_patterns = [
        r'^(?:/|/home|/index)',
        r'/products?',
        r'/shop',
        r'/catalog',
    ]

    high_priority_patterns = [
        r'/products?/[\w-]+',
        r'/item/[\w-]+',
        r'/product/[\w-]+',
        r'/sales',
        r'/promotion',
        r'/deals',
        r'/discount',
        r'/offer',
        r'/landing',
        r'/lp/',
        r'/campaign/',
        r'/about',
        r'/contact',
        r'/help',
        r'/support',
        r'/faq',
        r'/pricing',
        r'/features',
    ]

    medium_priority_patterns = [
        r'/blog',
        r'/news',
        r'/services',
        r'/cart',
    ]

    low_priority_patterns = [
        r'/privacy',
        r'/terms',
        r'/legal',
        r'/cookies',
        r'/sitemap',
        r'/search',
        r'/login',
        r'/register',
        r'/account',
        r'/checkout',
        r'/payment',
    ]

    scored_links = []
    for link in links:
        path = link['path'].lower()
        score = 0

        for pattern in highest_priority_patterns:
            if re.match(pattern, path):
                score += 15
                break
        else:
            for pattern in high_priority_patterns:
                if re.search(pattern, path):
                    score += 10
                    break
            else:
                for pattern in medium_priority_patterns:
                    if re.search(pattern, path):
                        score += 5
                        break

        for pattern in low_priority_patterns:
            if re.search(pattern, path):
                score -= 5
                break

        # Prefer shorter paths (closer to root)
        score -= len(path.split('/'))

        scored_links.append((score, link))

    scored_links.sort(key=lambda x: -x[0])
    selected = [link['url'] for score, link in scored_links[:max_pages]]
    print(f"Heuristic selection: chose {len(selected)} pages from {len(links)} total", file=sys.stderr)

    return selected


def analyze_site_structure_with_ai(links, api_base, api_key, model='gpt-4o', max_pages=20):
    """Use AI to analyze site structure and select most important pages."""
    if not links:
        return []

    link_summary = []
    for i, link in enumerate(links[:100]):
        text = link['text'] or link['title'] or link['path']
        link_summary.append(f"{i+1}. {link['path'][:60]} - '{text}'")

    links_text = '\n'.join(link_summary)

    prompt = f"""你是一个网站分析专家。给定一个网站的链接列表，请分析网站结构并选出最能代表网站核心内容的页面。

任务：
1. 识别页面类型（首页、产品页、产品详情、sales推广页、推广落地页、关于我们、博客、帮助中心等）
2. 评估每个页面的重要性（对了解网站目标受众和地区适配的价值）
3. 选出 {max_pages} 个最重要的页面进行分析

优先级规则（从高到低）：
**最高优先级 - 必须包含：**
- 首页（/、/home、/index）
- 产品列表页（/products、/shop、/catalog）

**高优先级 - 优先包含：**
- 产品详情页（/products/xxx、/item/xxx、/product/xxx）
- Sales 推广页（/sales、/promotion、/deals、/discount、/offer）
- 推广落地页（/lp/、/landing/、/campaign/）

**中优先级 - 视情况包含：**
- 关于我们（/about、/company）
- 联系我们（/contact）
- 帮助中心/FAQ（/help、/support、/faq）
- 价格页（/pricing、/plans）
- 购物车（/cart）- 转化关键页面

**低优先级 - 尽量避免：**
- 隐私政策、服务条款等法律页面
- 登录、注册、账户管理
- 结账流程（/checkout、/payment）
- 站点地图、搜索

链接列表：
{links_text}

请以JSON格式返回，包含以下字段：
- selected_indices: 选中的链接索引数组（0-based）
- reasoning: 简要说明选择逻辑，特别说明优先选择的产品、推广页面
- page_types: 识别出的主要页面类型

返回示例：
{{
  "selected_indices": [0, 3, 7, 15, 23, ...],
  "reasoning": "优先选择了产品列表、产品详情、sales推广页、关于我们、帮助中心等核心页面",
  "page_types": ["首页", "产品列表", "产品详情", "推广页", "关于我们", "帮助中心"]
}}
"""

    messages = [
        {'role': 'system', 'content': '你是网站分析专家，擅长识别网站结构和核心页面。'},
        {'role': 'user', 'content': prompt}
    ]

    response = _call_ai_api(messages, api_base, api_key, model)

    if isinstance(response, dict) and 'error' in response:
        print(f"Warning: AI site structure analysis failed: {response['error']}", file=sys.stderr)
        return select_pages_heuristically(links, max_pages)

    try:
        result = json.loads(response)
        selected_indices = result.get('selected_indices', [])
        reasoning = result.get('reasoning', '')
        page_types = result.get('page_types', [])

        print(f"AI 分析识别的页面类型: {', '.join(page_types)}", file=sys.stderr)
        print(f"AI 选择逻辑: {reasoning}", file=sys.stderr)

        selected_urls = []
        for idx in selected_indices:
            if idx < len(links):
                selected_urls.append(links[idx]['url'])

        return selected_urls

    except (json.JSONDecodeError, KeyError, IndexError) as e:
        print(f"Warning: Failed to parse AI response: {e}", file=sys.stderr)
        return select_pages_heuristically(links, max_pages)


# ── Sitemap discovery ─────────────────────────────────────────────────────────

def discover_sitemap(base_url, max_pages=50, timeout=15):
    """
    Try to discover and parse XML sitemap.

    Returns: {
        'urls': [...],
        'sitemap_url': str,
        'source': 'robots.txt' | 'standard_location' | 'none'
    }
    """
    parsed = urllib.parse.urlparse(base_url)
    domain = parsed.netloc

    sitemap_candidates = [
        f"https://{domain}/sitemap.xml",
        f"http://{domain}/sitemap.xml",
        f"https://{domain}/sitemap_index.xml",
        f"http://{domain}/sitemap_index.xml",
    ]

    # Also check robots.txt for sitemap location
    robots_url = f"https://{domain}/robots.txt"
    try:
        robots_html, _, _ = fetch_html(robots_url, timeout)
        if robots_html:
            sitemap_match = re.search(r'Sitemap:\s*(https?://[^\s]+)', robots_html, re.IGNORECASE)
            if sitemap_match:
                sitemap_url = sitemap_match.group(1)
                sitemap_candidates.insert(0, sitemap_url)
                print(f"[Smart Crawl] Found sitemap in robots.txt: {sitemap_url}", file=sys.stderr)
    except Exception as e:
        print(f"[Smart Crawl] Could not check robots.txt: {e}", file=sys.stderr)

    for sitemap_url in sitemap_candidates:
        try:
            print(f"[Smart Crawl] Checking for sitemap: {sitemap_url}", file=sys.stderr)
            sitemap_xml, _, _ = fetch_html(sitemap_url, timeout)

            if sitemap_xml:
                if HAS_BS4:
                    soup = BeautifulSoup(sitemap_xml, 'xml')

                    sitemap_tags = soup.find_all('sitemap')
                    if sitemap_tags:
                        print(f"[Smart Crawl] Found sitemap index with {len(sitemap_tags)} sitemaps", file=sys.stderr)
                        urls = []
                        for tag in sitemap_tags:
                            loc = tag.find('loc')
                            if loc and loc.text:
                                urls.append(loc.text.strip())
                        return {
                            'urls': urls[:max_pages],
                            'sitemap_url': sitemap_url,
                            'source': 'sitemap_index' if len(sitemap_tags) > 0 else 'standard_location'
                        }

                    url_tags = soup.find_all('url')
                    if url_tags:
                        print(f"[Smart Crawl] Found sitemap with {len(url_tags)} URLs", file=sys.stderr)
                        urls = []
                        for tag in url_tags:
                            loc = tag.find('loc')
                            if loc and loc.text:
                                urls.append(loc.text.strip())
                        return {
                            'urls': urls[:max_pages],
                            'sitemap_url': sitemap_url,
                            'source': 'robots.txt' if 'robots.txt' in str(sitemap_url) else 'standard_location'
                        }
                else:
                    url_matches = re.findall(r'<loc>\s*(https?://[^<]+)\s*</loc>', sitemap_xml)
                    if url_matches:
                        print(f"[Smart Crawl] Found sitemap with {len(url_matches)} URLs (regex)", file=sys.stderr)
                        return {
                            'urls': url_matches[:max_pages],
                            'sitemap_url': sitemap_url,
                            'source': 'robots.txt' if 'robots.txt' in str(sitemap_url) else 'standard_location'
                        }

        except Exception as e:
            print(f"[Smart Crawl] Failed to fetch/parse {sitemap_url}: {e}", file=sys.stderr)
            continue

    return {
        'urls': [],
        'sitemap_url': None,
        'source': 'none'
    }


# ── BFS crawl ─────────────────────────────────────────────────────────────────

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


# ── Smart crawl ───────────────────────────────────────────────────────────────

def crawl_site_smart(start_url, max_pages=20, timeout=15, delay=1.0,
                     progress_callback=None, use_ai=True,
                     ai_api_base=None, ai_api_key=None, ai_model='gpt-4o'):
    """
    Smart crawling:
    1. Try to find sitemap.xml first
    2. If no sitemap, extract navigation links from homepage
    3. Use AI/heuristics to select most important pages
    4. Fetch selected pages

    Returns: {
        'results': [...],
        'site_map': {
            'total_links': N,
            'selected_pages': K,
            'selection_method': 'sitemap' | 'navigation' | 'ai' | 'heuristic',
            'page_types': [...],
            'reasoning': '...'
        }
    }
    """
    start_normalized = _normalize_url(start_url)

    print(f"[Smart Crawl] Starting with: {start_normalized}", file=sys.stderr)

    # Step 1: Try to discover sitemap
    print(f"[Smart Crawl] Step 1: Looking for sitemap...", file=sys.stderr)
    sitemap_result = discover_sitemap(start_normalized, timeout)

    if sitemap_result['urls']:
        print(f"[Smart Crawl] Found sitemap with {len(sitemap_result['urls'])} URLs", file=sys.stderr)
        sitemap_urls = sitemap_result['urls'][:max_pages]

        print(f"[Smart Crawl] Step 2: Fetching homepage...", file=sys.stderr)
        html, final_url, err = fetch_html(start_normalized, timeout)
        if not html:
            print(f"[Smart Crawl] Failed to fetch homepage", file=sys.stderr)
            html = None
            final_url = start_normalized

        results = []
        if html:
            results.append({
                'url': start_normalized,
                'html': html,
                'depth': 0,
                'final_url': final_url or start_normalized,
            })

        print(f"[Smart Crawl] Step 3: Fetching {len(sitemap_urls)} pages from sitemap...", file=sys.stderr)
        for i, url in enumerate(sitemap_urls):
            if url == start_normalized or url == start_url:
                continue  # Skip homepage

            if len(results) >= max_pages:
                break

            if progress_callback:
                progress_callback(len(results) + 1, url)

            time.sleep(delay)

            html, final_url, err = fetch_html(url, timeout)
            if html:
                results.append({
                    'url': url,
                    'html': html,
                    'depth': 1,
                    'final_url': final_url or url,
                })
                print(f"[Smart Crawl] Fetched {len(results)}: {url[:60]}...", file=sys.stderr)
            else:
                print(f"[Smart Crawl] Failed to fetch: {url}", file=sys.stderr)

        site_map = {
            'total_links': len(sitemap_result['urls']),
            'selected_pages': len(results),
            'selection_method': 'sitemap',
            'sitemap_source': sitemap_result['source'],
            'page_types': ['Sitemap-provided'],
            'reasoning': f'Used sitemap from {sitemap_result["source"]}'
        }

        print(f"[Smart Crawl] Complete! Fetched {len(results)} pages via sitemap", file=sys.stderr)

        return {
            'results': results,
            'site_map': site_map
        }

    # No sitemap found - use navigation links
    print(f"[Smart Crawl] No sitemap found, extracting navigation links...", file=sys.stderr)

    print(f"[Smart Crawl] Step 2: Fetching homepage...", file=sys.stderr)
    html, final_url, err = fetch_html(start_normalized, timeout)
    if not html:
        print(f"[Smart Crawl] Failed to fetch homepage", file=sys.stderr)
        return {
            'results': crawl_site(start_url, max_depth=1, max_pages=max_pages,
                                  timeout=timeout, delay=delay, progress_callback=progress_callback),
            'site_map': {'total_links': 0, 'selected_pages': 0,
                          'selection_method': 'fallback', 'page_types': [], 'reasoning': 'Failed to fetch homepage'}
        }

    results = [{
        'url': start_normalized,
        'html': html,
        'depth': 0,
        'final_url': final_url or start_normalized,
    }]

    print(f"[Smart Crawl] Step 3: Extracting navigation links...", file=sys.stderr)
    nav_links = extract_navigation_links(html, final_url or start_normalized)
    print(f"[Smart Crawl] Found {len(nav_links)} navigation links", file=sys.stderr)

    if not nav_links:
        print(f"[Smart Crawl] No navigation links found, extracting all links...", file=sys.stderr)
        nav_links = extract_links_with_metadata(html, final_url or start_normalized)

    print(f"[Smart Crawl] Step 4: Selecting {max_pages-1} important pages...", file=sys.stderr)

    selected_urls = []
    page_types = []
    reasoning = ''
    selection_method = 'heuristic'

    if use_ai and ai_api_base and ai_api_key:
        try:
            selected_urls = analyze_site_structure_with_ai(
                nav_links, ai_api_base, ai_api_key, ai_model, max_pages-1
            )
            selection_method = 'ai'
            page_types = ['AI-selected from navigation']
            reasoning = 'AI analyzed navigation links and selected most representative pages'
        except Exception as e:
            print(f"[Smart Crawl] AI selection failed, using heuristics: {e}", file=sys.stderr)
            selected_urls = [link['url'] for link in nav_links[:max_pages-1]]
            selection_method = 'heuristic'
            page_types = ['Navigation links']
            reasoning = 'Used navigation links (heuristic selection)'
    else:
        selected_urls = [link['url'] for link in nav_links[:max_pages-1]]
        selection_method = 'heuristic'
        page_types = ['Navigation links']
        reasoning = 'Used navigation links (no AI configured)'

    print(f"[Smart Crawl] Selected {len(selected_urls)} pages via {selection_method}", file=sys.stderr)

    print(f"[Smart Crawl] Step 5: Fetching {len(selected_urls)} selected pages...", file=sys.stderr)
    for i, url in enumerate(selected_urls):
        if progress_callback:
            progress_callback(i + 2, url)

        time.sleep(delay)

        html, final_url, err = fetch_html(url, timeout)
        if html:
            results.append({
                'url': url,
                'html': html,
                'depth': 1,
                'final_url': final_url or url,
            })
            print(f"[Smart Crawl] Fetched {i+1}/{len(selected_urls)}: {url[:60]}...", file=sys.stderr)
        else:
            print(f"[Smart Crawl] Failed to fetch: {url}", file=sys.stderr)

    site_map = {
        'total_links': len(nav_links),
        'selected_pages': len(results),
        'selection_method': selection_method,
        'page_types': page_types,
        'reasoning': reasoning
    }

    print(f"[Smart Crawl] Complete! Fetched {len(results)} pages total", file=sys.stderr)

    return {
        'results': results,
        'site_map': site_map
    }
