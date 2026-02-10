#!/usr/bin/env python3
"""
Generate Markdown report from JSON analysis results
"""
import json
import sys
from datetime import datetime


def _dedupe_keep_order(values):
    seen = set()
    output = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        output.append(value)
    return output


def generate_markdown_report(data):
    """Generate a comprehensive Markdown report from analysis data"""

    md = []
    result = data.get('siteResult') if data.get('mode') == 'site' else data.get('result')
    optimization = data.get('siteOptimization') if data.get('mode') == 'site' else data.get('optimization')
    optimization_summary = optimization.get('summary', {}) if optimization else {}
    critical_count = optimization_summary.get('critical', 0)
    warning_count = optimization_summary.get('warnings', 0)

    # Header
    md.append("# 网站分析报告\n")
    md.append(f"**分析时间**: {data.get('analyzedAt', 'N/A')}\n")
    md.append(f"**分析模式**: {'多页面站点分析' if data.get('mode') == 'site' else '单页面分析'}\n")
    md.append(f"**目标网站**: {data.get('url', 'N/A')}\n")

    # Executive summary
    md.append("\n## 🧭 执行摘要\n")
    if result:
        confidence = result.get('regionConfidence', 0)
        md.append(f"- 目标地区：**{result.get('primaryRegionName', 'Unknown')}**（{result.get('primaryRegion', 'N/A')}）\n")
        md.append(f"- 主要语言：**{result.get('primaryLanguageName', 'Unknown')}**（{result.get('primaryLanguage', 'N/A')}）\n")
        md.append(f"- 目标受众：**{result.get('likelyAudience', 'N/A')}**\n")
        md.append(f"- 地区置信度：**{confidence:.2f}**\n")
    else:
        md.append("- 暂无可用的地区与受众结论。\n")

    if optimization:
        score = optimization_summary.get('score', 0)
        grade = optimization_summary.get('grade', 'N/A')
        md.append(f"- 本地化评分：**{score}/100（{grade}）**\n")
        md.append(f"- 问题概览：关键问题 **{critical_count}** 项，警告 **{warning_count}** 项\n")
    else:
        md.append("- 暂无本地化优化评分数据。\n")

    # Crawl Summary (if site mode)
    if data.get('mode') == 'site' and data.get('crawlSummary'):
        summary = data['crawlSummary']
        md.append("\n## 📊 爬取摘要\n")
        md.append(f"- **分析页面数**: {summary.get('pagesAnalyzed', 0)}\n")
        md.append(f"- **最大爬取深度**: {summary.get('maxDepthReached', 0)}\n")
        md.append(f"- **页面列表**:\n")
        for url in summary.get('pageUrls', [])[:10]:  # Show first 10
            md.append(f"  - {url}\n")
        if len(summary.get('pageUrls', [])) > 10:
            md.append(f"  - ... 及其他 {len(summary['pageUrls']) - 10} 个页面\n")

    # Main Results
    if result:
        md.append("\n## 🎯 地区与受众分析\n")
        md.append(f"### 主要结论\n")
        md.append(f"- **目标地区**: {result.get('primaryRegionName', 'Unknown')} ({result.get('primaryRegion', 'N/A')})\n")
        md.append(f"- **主要语言**: {result.get('primaryLanguageName', 'Unknown')} ({result.get('primaryLanguage', 'N/A')})\n")
        md.append(f"- **目标受众**: {result.get('likelyAudience', 'N/A')}\n")

        confidence = result.get('regionConfidence', 0)
        confidence_level = "高" if confidence > 0.6 else "中" if confidence > 0.3 else "低"
        confidence_emoji = "🟢" if confidence > 0.6 else "🟡" if confidence > 0.3 else "🔴"
        md.append(f"- **地区置信度**: {confidence:.2f} {confidence_emoji} ({confidence_level}置信度)\n")

        # Confidence interpretation
        md.append(f"\n### 置信度解读\n")
        if confidence > 0.6:
            md.append("✅ **高置信度** - 多个信号一致指向同一地区，判断可靠。\n")
        elif confidence > 0.3:
            md.append("⚠️ **中等置信度** - 部分信号一致，但存在缺失或冲突。\n")
        else:
            md.append("🔴 **低置信度** - 这通常表明网站是全球化站点，缺乏明确的地区信号。对于跨境电商来说这是正常的。\n")

    # Evidence Analysis
    if data.get('mode') == 'site':
        # For site mode, use first page's evidence as example
        evidence = data.get('pages', [{}])[0].get('evidence', {})
    else:
        evidence = data.get('evidence', {})

    if evidence:
        md.append("\n## 🔍 信号分析\n")

        # HTML Signals
        html_signals = evidence.get('htmlSignals', {})
        if html_signals:
            md.append("### HTML 元数据信号\n")
            md.append(f"- **语言声明**: `<html lang=\"{html_signals.get('lang', 'N/A')}\">`\n")
            md.append(f"- **字符集**: {html_signals.get('charset', 'N/A')}\n")
            md.append(f"- **og:locale**: {html_signals.get('metaLocale') or '❌ 未设置'}\n")
            md.append(f"- **content-language**: {html_signals.get('metaLanguage') or '❌ 未设置'}\n")
            md.append(f"- **hreflang 标签**: {len(html_signals.get('hreflangTags', [])) or '❌ 未设置'}\n")
            md.append(f"- **顶级域名**: {html_signals.get('tld') or '.com (通用)'}\n")

        # Content Signals
        content_signals = evidence.get('contentSignals', {})
        if content_signals:
            md.append("\n### 内容信号\n")
            currencies = _dedupe_keep_order(
                content_signals.get('currencySymbols', []) + content_signals.get('currencyCodes', [])
            )
            if currencies:
                md.append(f"- **货币**: {', '.join(currencies)}\n")
            else:
                md.append(f"- **货币**: 未检测到\n")

            phones = _dedupe_keep_order(content_signals.get('phoneFormats', []))
            if phones:
                md.append(f"- **电话格式**: {', '.join(phones)}\n")

            payments = content_signals.get('paymentMethods', [])
            if payments:
                payment_methods = _dedupe_keep_order([p.get('method', 'N/A') for p in payments])
                md.append(f"- **支付方式**: {', '.join(payment_methods)}\n")

            social = content_signals.get('socialMediaSignals', [])
            if social:
                social_domains = _dedupe_keep_order([s.get('domain', 'N/A') for s in social])
                md.append(f"- **社交媒体**: {', '.join(social_domains)}\n")

            spelling = content_signals.get('spellingCounts', {})
            if spelling:
                us_count = spelling.get('US', 0)
                uk_count = spelling.get('UK', 0)
                if us_count > uk_count:
                    md.append(f"- **拼写习惯**: 美式英语 ({us_count} 处)\n")
                elif uk_count > us_count:
                    md.append(f"- **拼写习惯**: 英式英语 ({uk_count} 处)\n")

        # IP Geolocation
        ip_geo = evidence.get('ipGeolocation', {})
        if ip_geo and ip_geo.get('status') == 'success':
            md.append("\n### 服务器信息\n")
            md.append(f"- **服务器位置**: {ip_geo.get('city', 'N/A')}, {ip_geo.get('country', 'N/A')}\n")
            md.append(f"- **ISP**: {ip_geo.get('isp', 'N/A')}\n")
            md.append(f"- **组织**: {ip_geo.get('org', 'N/A')}\n")

            # CDN detection
            isp = ip_geo.get('isp', '').lower()
            org = ip_geo.get('org', '').lower()
            if any(cdn in isp or cdn in org for cdn in ['cloudflare', 'akamai', 'fastly', 'cloudfront']):
                md.append(f"- **CDN**: ✅ 已检测到 CDN（全球分发）\n")

    # Optimization Report
    if optimization:
        md.append("\n## 📈 本地化优化评分\n")

        score = optimization_summary.get('score', 0)
        grade = optimization_summary.get('grade', 'N/A')

        # Grade emoji
        grade_emoji = {
            'A': '🟢', 'B': '🟡', 'C': '🟠', 'D': '🔴', 'F': '⚫'
        }.get(grade, '⚪')

        md.append(f"### 总体评分\n")
        md.append(f"- **分数**: {score}/100\n")
        md.append(f"- **等级**: {grade_emoji} {grade}\n")
        md.append(f"- **问题总数**: {optimization_summary.get('totalIssues', 0)}\n")
        md.append(f"  - 🔴 关键问题: {critical_count}\n")
        md.append(f"  - 🟡 警告: {warning_count}\n")
        md.append(f"  - 🔵 信息: {optimization_summary.get('info', 0)}\n")

        # Grade interpretation
        md.append(f"\n### 评分解读\n")
        if score >= 80:
            md.append("✅ **优秀** - 本地化配置完善，仅有少量非关键建议。\n")
        elif score >= 60:
            md.append("🟡 **良好** - 基本配置到位，存在一些警告项需要改进。\n")
        elif score >= 40:
            md.append("🟠 **及格** - 存在较多问题，建议优先修复关键问题。\n")
        elif score >= 20:
            md.append("🔴 **较差** - 存在关键缺失，严重影响国际化效果。\n")
        else:
            md.append("⚫ **极差** - 基本未做本地化配置，需要全面改进。\n")

        # Recommendations
        recommendations = optimization.get('recommendations', [])
        if recommendations:
            md.append("\n## 🚨 优化建议\n")

            # Group by severity
            critical = [r for r in recommendations if r.get('severity') == 'critical']
            warnings = [r for r in recommendations if r.get('severity') == 'warning']
            info = [r for r in recommendations if r.get('severity') == 'info']

            if critical:
                md.append("\n### 🔴 关键问题（必须修复）\n")
                for i, rec in enumerate(critical, 1):
                    md.append(f"\n#### {i}. {rec.get('category', 'N/A')}\n")
                    md.append(f"**问题**: {rec.get('issue', 'N/A')}\n\n")
                    md.append(f"**建议**: {rec.get('recommendation', 'N/A')}\n\n")
                    if rec.get('codeExample'):
                        md.append(f"**代码示例**:\n```html\n{rec['codeExample']}\n```\n")

            if warnings:
                md.append("\n### 🟡 警告问题（应该修复）\n")
                for i, rec in enumerate(warnings, 1):
                    md.append(f"\n#### {i}. {rec.get('category', 'N/A')}\n")
                    md.append(f"**问题**: {rec.get('issue', 'N/A')}\n\n")
                    md.append(f"**建议**: {rec.get('recommendation', 'N/A')}\n\n")
                    if rec.get('codeExample'):
                        md.append(f"**代码示例**:\n```html\n{rec['codeExample']}\n```\n")

            if info:
                md.append("\n### 🔵 信息建议（可选优化）\n")
                for i, rec in enumerate(info, 1):
                    md.append(f"\n#### {i}. {rec.get('category', 'N/A')}\n")
                    md.append(f"{rec.get('issue', 'N/A')}\n\n")

    # Next actions
    if optimization:
        md.append("\n## ✅ 建议优先处理\n")
        if critical_count > 0:
            md.append(f"- 当前存在关键问题 {critical_count} 项，请优先处理关键问题。\n")
        elif warning_count > 0:
            md.append(f"- 当前无关键问题，建议先处理警告问题 {warning_count} 项。\n")
        else:
            md.append("- 当前无关键/警告问题，可按需处理信息级建议。\n")

    # Errors and Warnings
    errors = data.get('errors', [])
    warnings = data.get('warnings', [])

    if errors or warnings:
        md.append("\n## ⚠️ 分析过程中的问题\n")
        if errors:
            md.append("\n### 错误\n")
            for error in errors:
                md.append(f"- ❌ {error}\n")
        if warnings:
            md.append("\n### 警告\n")
            for warning in warnings:
                md.append(f"- ⚠️ {warning}\n")

    # Footer
    md.append("\n---\n")
    md.append("*报告由 Web Region & Audience Analyzer 生成*\n")

    return ''.join(md)


def main():
    if len(sys.argv) < 2:
        print("Usage: python generate_markdown_report.py <json_file> [output_file]")
        sys.exit(1)

    json_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    markdown = generate_markdown_report(data)

    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(markdown)
        print(f"Markdown report saved to: {output_file}")
    else:
        print(markdown)


if __name__ == '__main__':
    main()
