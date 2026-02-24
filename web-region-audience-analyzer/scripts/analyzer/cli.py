"""
CLI entry point for the Web Region & Audience Analyzer.
"""
import json
import os
import sys

from .core import analyze, analyze_site
from .html_parsing import HAS_BS4


def main():
    import argparse
    from datetime import datetime

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
    parser.add_argument('--format', choices=['json', 'markdown', 'friendly'], default='json',
                        help='Output format: json, markdown, or friendly (default: json)')
    parser.add_argument('--no-recommendations', action='store_true',
                        help='Disable cross-border optimization recommendations')
    parser.add_argument('--target-audience',
                        help='Optional target audience input. If omitted, AI (or rule-based fallback) will infer audience before persona fit analysis.')

    crawl_group = parser.add_argument_group('multi-page crawling')
    crawl_group.add_argument('--no-crawl', action='store_true',
                             help='Disable multi-page site crawling (analyze single page only)')
    crawl_group.add_argument('--max-depth', type=int, default=3,
                             help='Maximum crawl depth (default: 3, ignored with --smart-crawl)')
    crawl_group.add_argument('--max-pages', type=int, default=50,
                             help='Maximum pages to crawl (default: 50)')
    crawl_group.add_argument('--smart-crawl', action='store_true',
                             help='Use AI-driven smart crawling (analyze structure first, then select important pages)')

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
            use_smart_crawl=args.smart_crawl,
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
    if args.format in ['markdown', 'friendly']:
        import subprocess
        import tempfile

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as tmp:
            json.dump(result, tmp, indent=2, ensure_ascii=False)
            tmp_path = tmp.name

        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if args.format == 'friendly':
            md_script = os.path.join(script_dir, 'generate_user_friendly_report.py')
        else:
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

    # Determine output path
    output_path = args.output
    if args.format in ['markdown', 'friendly'] and not output_path:
        # Try to use export_utils from parent scripts dir
        try:
            import sys as _sys
            _scripts_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            if _scripts_dir not in _sys.path:
                _sys.path.insert(0, _scripts_dir)
            from export_utils import build_default_markdown_output_path
            output_path = build_default_markdown_output_path(args.url)
        except ImportError:
            fallback_name = f"web-region-audience-report-{datetime.now().strftime('%Y%m%d-%H%M%S')}.md"
            output_path = os.path.join(os.path.expanduser('~'), 'Downloads', fallback_name)

    if output_path:
        output_dir = os.path.dirname(os.path.abspath(output_path))
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(out)
        if args.format == 'friendly':
            print(f"📋 用户友好报告已保存至: {output_path}")
        else:
            print(f"Markdown report saved to: {output_path}")
    else:
        print(out)
