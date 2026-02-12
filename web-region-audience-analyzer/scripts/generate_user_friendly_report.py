#!/usr/bin/env python3
"""
Generate user-friendly Markdown report from JSON analysis results
With easy-to-understand explanations and action steps
"""
import json
import sys
from datetime import datetime


def generate_user_friendly_report(data):
    """Generate a comprehensive, user-friendly Markdown report"""
    
    md = []
    result = data.get('siteResult') if data.get('mode') == 'site' else data.get('result')
    optimization = data.get('siteOptimization') if data.get('mode') == 'site' else data.get('optimization')
    persona = data.get('personaAnalysis')
    
    # Get optimization summary
    optimization_summary = optimization.get('summary', {}) if optimization else {}
    critical_count = optimization_summary.get('critical', 0)
    warning_count = optimization_summary.get('warnings', 0)
    
    # ╔═══════════════════════════════════════════════════════════════════════╗
    # ║                    🌐 网站本地化分析报告                         ║
    # ╚═══════════════════════════════════════════════════════════════════════╝
    
    md.append("# 🌐 网站本地化分析报告\n")
    md.append("---\n")
    md.append(f"**分析时间**: {data.get('analyzedAt', 'N/A')[:10] if data.get('analyzedAt') else 'N/A'}\n")
    md.append(f"**分析模式**: {'🔍 多页面站点分析' if data.get('mode') == 'site' else '📄 单页面分析'}\n")
    md.append(f"**目标网站**: {data.get('url', 'N/A')}\n")
    
    # ╔═══════════════════════════════════════════════════════════════════════╗
    # ║                        📊 总体评分                              ║
    # ╚═══════════════════════════════════════════════════════════════════════╝
    
    md.append("\n## 📊 总体评分\n")
    
    if optimization:
        score = optimization_summary.get('score', 0)
        grade = optimization_summary.get('grade', 'N/A')
        
        # Grade display
        grade_map = {
            'A': {'emoji': '🟢', 'text': '优秀', 'desc': '几乎完美，只需少量优化'},
            'B': {'emoji': '🟢', 'text': '良好', 'desc': '存在一些小问题'},
            'C': {'emoji': '🟠', 'text': '及格', 'desc': '存在一些重要问题需要修复'},
            'D': {'emoji': '🔴', 'text': '较差', 'desc': '存在关键缺失，严重影响效果'},
            'F': {'emoji': '🔴', 'text': '极差', 'desc': '几乎未做本地化配置'},
        }
        grade_info = grade_map.get(grade, {'emoji': '⚪', 'text': '未知', 'desc': ''})
        
        md.append(f"### 当前状态\n")
        md.append(f"- **本地化评分**: **{score}/100** {grade_info['emoji']} **{grade}级 - {grade_info['text']}\n")
        md.append(f"- **问题总数**: **{critical_count + warning_count}** 个\n")
        md.append(f"  - 🔴 关键问题: **{critical_count}** 个（必须修复）\n")
        md.append(f"  - 🟡 警告问题: **{warning_count}** 个（建议修复）\n")
        md.append(f"\n{grade_info['desc']}\n")
    else:
        md.append("暂无评分数据。\n")
    
    # ╔═══════════════════════════════════════════════════════════════════════╗
    # ║                      🎯 核心发现                              ║
    # ╚═══════════════════════════════════════════════════════════════════════╝
    
    md.append("\n## 🎯 核心发现\n")
    
    if result:
        md.append(f"- **目标地区**: 🏳️ {result.get('primaryRegionName', 'Unknown')} ({result.get('primaryRegion', 'N/A')})\n")
        md.append(f"- **主要语言**: 🗣️ {result.get('primaryLanguageName', 'Unknown')} ({result.get('primaryLanguage', 'N/A')})\n")
        md.append(f"- **目标受众**: 👥 {result.get('likelyAudience', 'Unknown')}\n")
    else:
        md.append("- 暂无可用的地区与受众结论。\n")
    
    # ╔═══════════════════════════════════════════════════════════════════════╗
    # ║                   ✅ 已经做对的事情                           ║
    # ╚═══════════════════════════════════════════════════════════════════════╝
    
    md.append("\n## ✅ 已经做对的事情\n")
    
    done_right = []
    if result:
        evidence = data.get('evidence', {}) if data.get('mode') == 'page' else {}
        if data.get('mode') == 'site':
            # Get first page's evidence
            pages = data.get('pages', [])
            if pages:
                evidence = pages[0].get('evidence', {})
        
        html_signals = evidence.get('htmlSignals', {})
        
        if html_signals.get('lang'):
            done_right.append(f"✅ 声明了页面语言：`<html lang=\"{html_signals['lang']}\">`")
        
        if html_signals.get('hreflangTags') and len(html_signals['hreflangTags']) > 0:
            done_right.append(f"✅ 存在 hreflang 标签（{len(html_signals['hreflangTags'])} 个）")
        
        if evidence.get('ipGeolocation') and 'error' not in evidence.get('ipGeolocation', {}):
            geo = evidence.get('ipGeolocation', {})
            done_right.append(f"✅ 服务器位于 {geo.get('countryName', 'Unknown')}（{geo.get('isp', 'N/A')}）")
    
    if done_right:
        for item in done_right:
            md.append(f"- {item}\n")
    else:
        md.append("- 暂未检测到明显的正确配置。\n")
    
    # ╔═══════════════════════════════════════════════════════════════════════╗
    # ║                   🚨 最需要修复的问题                          ║
    # ╚═══════════════════════════════════════════════════════════════════════╝
    
    md.append("\n## 🚨 最需要修复的问题\n")
    
    if optimization and optimization.get('recommendations'):
        # Categorize recommendations
        critical_recs = [r for r in optimization['recommendations'] if r.get('severity') == 'critical']
        warning_recs = [r for r in optimization['recommendations'] if r.get('severity') == 'warning']
        
        if critical_recs:
            md.append("\n### 🔴 必须修复（关键问题）\n")
            for i, rec in enumerate(critical_recs[:3], 1):  # Show top 3
                md.append(f"\n#### {i}. {rec.get('category', 'Unknown')}\n")
                md.append(f"\n**问题**: {rec.get('issue', 'Unknown')}\n")
                
                # Add explanation for common issues
                category = rec.get('category', '')
                
                if category == 'hreflang':
                    md.append(f"\n📖 **这是什么问题？**\n")
                    md.append("搜索引擎不知道你的网站有其他语言/地区版本。\n")
                    md.append("中国用户可能看到英文页面，不知道应该给他们看哪个版本。\n")
                    md.append(f"\n⚠️ **为什么重要？**\n")
                    md.append("- 中国用户搜索相关关键词时，可能看不到中文版本\n")
                    md.append("- 可能导致错误的语言版本被索引\n")
                    md.append("- 搜索引擎可能认为这是重复内容\n")
                elif category == 'locale-declaration':
                    md.append(f"\n📖 **这是什么问题？**\n")
                    md.append("网页没有明确声明语言，浏览器和屏幕阅读器无法正确识别。\n")
                    md.append(f"\n⚠️ **为什么重要？**\n")
                    md.append("- 浏览器无法提供正确的翻译建议\n")
                    md.append("- 屏幕阅读器可能发音错误\n")
                elif category == 'accessibility':
                    md.append(f"\n📖 **这是什么问题？**\n")
                    md.append("图片缺少 alt 文本描述。\n")
                    md.append(f"\n⚠️ **为什么重要？**\n")
                    md.append("- 视障用户无法了解图片内容\n")
                    md.append("- 图片无法被搜索引擎正确理解\n")
                    md.append("- 影响网站的无障碍访问合规性\n")
                
                # Fix steps
                md.append(f"\n🔧 **修复方法**（根据你的平台）：\n")
                
                md.append(f"\n🛒 **如果你用 Shopify**：\n")
                md.append("1. 进入 Shopify 后台\n")
                md.append("2. 在线商店 → 市场\n")
                md.append("3. 点击「管理语言市场」\n")
                md.append("4. 添加/编辑目标语言\n")
                md.append("5. 保存更改\n")
                
                md.append(f"\n📗 **如果你用 WordPress**（需要插件）：\n")
                md.append("1. 安装 Yoast SEO 或 Rank Math 插件\n")
                md.append("2. 进入 SEO → 高级 → 架构\n")
                md.append("3. 启用相关功能\n")
                
                md.append(f"\n⚙️ **如果你用其他平台/自定义**：\n")
                if rec.get('codeExample'):
                    md.append("在 `<head>` 中添加以下代码：\n")
                    md.append(f"\n```html\n{rec.get('codeExample')}\n```\n")
                
                # Expected outcome
                if rec.get('expectedOutcome'):
                    md.append(f"\n{rec.get('expectedOutcome')}\n")
                
                # Learn more
                if rec.get('learnMore'):
                    md.append(f"\n{rec.get('learnMore')}\n")
        
        if warning_recs:
            md.append("\n---\n")
            md.append("\n### 🟡 建议修复（警告问题）\n")
            md.append("以下问题虽然不是致命的，但修复后可以提升用户体验：\n")
            
            for i, rec in enumerate(warning_recs[:3], 1):
                md.append(f"\n**{i}. {rec.get('category', 'Unknown')}**\n")
                md.append(f"- {rec.get('issue', 'Unknown')}\n")
                md.append(f"\n修复建议：{rec.get('issue', '')[:100]}...\n")
    
    # ╔═══════════════════════════════════════════════════════════════════════╗
    # ║                       📚 还想学习更多？                         ║
    # ╚═══════════════════════════════════════════════════════════════════════╝
    
    md.append("\n---\n")
    md.append("\n## 📚 还想学习更多？\n")
    
    md.append("\n📖 **官方指南**：\n")
    md.append("- Google 多语言 SEO 指南：https://developers.google.com/search/docs/advanced/crawling/multilingual-sites\n")
    md.append("- hreflang 完整指南：https://developers.google.com/search/docs/advanced/crawling/localization-of-sites\n")
    md.append("- Shopify 多语言设置：https://help.shopify.com/zh/manual/sell-online/online-store/multilingual\n")
    
    md.append("\n💬 **社区支持**：\n")
    md.append("- Reddit r/SEO：https://www.reddit.com/r/SEO/\n")
    md.append("- Reddit r/Shopify：https://www.reddit.com/r/Shopify/\n")
    md.append("- Reddit r/bigcommerce：https://www.reddit.com/r/bigcommerce/\n")
    
    md.append("\n🎓 **视频教程**（YouTube 搜索）：\n")
    md.append("- 「hreflang 教程」\n")
    md.append("- 「Shopify 多语言设置」\n")
    md.append("- 「SEO 多语言网站优化」\n")
    
    # ╔═══════════════════════════════════════════════════════════════════════╗
    # ║                           底部信息                                ║
    # ╚═══════════════════════════════════════════════════════════════════════╝
    
    md.append("\n---\n")
    md.append("*报告由 Web Region & Audience Analyzer 自动生成*\n")
    md.append(f"*生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}*\n")
    
    return '\n'.join(md)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        report = generate_user_friendly_report(data)
        print(report)
    else:
        print("Usage: generate_user_friendly_report.py <json_file>")
