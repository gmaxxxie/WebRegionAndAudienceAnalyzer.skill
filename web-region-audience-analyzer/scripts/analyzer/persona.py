"""
persona.py — Persona analysis: resolve audience, build fallback, compose analysis, create context.
"""
from .constants import COUNTRY_NAMES, LANG_NAMES


def resolve_target_audience(user_input, result, ai_analysis=None):
    """Resolve final target audience with priority: user input > AI > rule-based."""
    normalized_user_input = (user_input or '').strip()
    if normalized_user_input:
        return {
            'source': 'user_input',
            'userInput': normalized_user_input,
            'inferredAudience': None,
            'finalAudience': normalized_user_input,
        }

    inferred = None
    if isinstance(ai_analysis, dict):
        ta = ai_analysis.get('targetAudience', {})
        inferred = ta.get('finalAudience') or ta.get('inferredAudience')
        if not inferred:
            inferred = ai_analysis.get('inferredAudience')
        if isinstance(inferred, str):
            inferred = inferred.strip() or None
        else:
            inferred = None

    if inferred:
        return {
            'source': 'ai_inferred',
            'userInput': None,
            'inferredAudience': inferred,
            'finalAudience': inferred,
        }

    likely = None
    if isinstance(result, dict):
        likely = result.get('likelyAudience')
        if isinstance(likely, str):
            likely = likely.strip() or None
        else:
            likely = None

    if likely:
        return {
            'source': 'rule_based',
            'userInput': None,
            'inferredAudience': likely,
            'finalAudience': likely,
        }

    return {
        'source': 'rule_based',
        'userInput': None,
        'inferredAudience': 'Unknown audience',
        'finalAudience': 'Unknown audience',
    }


def build_fallback_persona_analysis(result, evidence, target_audience=None):
    """Build deterministic persona analysis when AI analysis is unavailable."""
    result = result or {}
    evidence = evidence or {}
    audience = resolve_target_audience(target_audience, result, ai_analysis=None)

    region_code = result.get('primaryRegion') or 'N/A'
    region_name = result.get('primaryRegionName') or 'Unknown'
    language_name = result.get('primaryLanguageName') or 'Unknown'

    confidence = result.get('regionConfidence', 0.0) or 0.0
    base_score = max(0.0, min(10.0, round(float(confidence) * 10, 1)))

    html_signals = evidence.get('htmlSignals', {})
    content_signals = evidence.get('contentSignals', {})

    matching_signals = []
    mismatch_signals = []

    if html_signals.get('lang'):
        matching_signals.append(f"声明了页面语言：{html_signals.get('lang')}")
        base_score += 0.4
    else:
        mismatch_signals.append("未声明 <html lang>，语言定位不够清晰")

    currencies = content_signals.get('currencySymbols', []) + content_signals.get('currencyCodes', [])
    if currencies:
        dedup_currencies = list(dict.fromkeys(currencies))
        matching_signals.append(f"检测到货币信号：{', '.join(dedup_currencies[:3])}")
        base_score += 0.6

    hreflangs = html_signals.get('hreflangTags', [])
    if hreflangs:
        matching_signals.append("存在 hreflang 标签，支持多地区人群识别")
        base_score += 0.4
    else:
        mismatch_signals.append("缺少 hreflang 标签，多地区人群覆盖信息不足")

    if not content_signals.get('paymentMethods'):
        mismatch_signals.append("页面未呈现明显的本地化支付方式信号")
    else:
        matching_signals.append("检测到本地支付方式信号")
        base_score += 0.3

    final_score = max(0.0, min(10.0, round(base_score, 1)))

    persona = {
        'regionCode': region_code,
        'regionName': region_name,
        'language': language_name,
        'personaLabel': f"{region_name} {audience.get('finalAudience', 'target audience')}",
        'traits': [
            '关注价格和价值比',
            '偏好清晰的配送与退换货信息',
            '倾向于移动端快速决策',
        ],
        'motivations': [
            '获得与本地区匹配的商品和文案',
            '降低支付和履约不确定性',
        ],
        'painPoints': [
            '语言/货币信息不一致导致决策成本高',
            '本地化信任要素不足（评价、保障、支付）',
        ],
        'purchaseDrivers': [
            '价格透明',
            '本地支付方式',
            '快速物流和明确售后',
        ],
    }

    summary = (
        "网站与该人群匹配度较好。"
        if final_score >= 7
        else "网站与该人群存在部分匹配缺口，建议优先修复本地化关键要素。"
    )

    return {
        'audience': audience,
        'regionalPersona': persona,
        'personaFit': {
            'score': final_score,
            'isFit': final_score >= 7,
            'matchingSignals': matching_signals[:10],
            'mismatchSignals': mismatch_signals[:10],
            'summary': summary,
        },
    }


def compose_persona_analysis(result, evidence, target_audience=None, ai_analysis=None, persona_context=None):
    """Compose persona analysis with optional persona context for enhanced evaluation."""
    if persona_context:
        audience = {
            'source': persona_context.get('source', 'rule_based'),
            'userInput': persona_context.get('userInput'),
            'inferredAudience': persona_context.get('inferredAudience'),
            'finalAudience': persona_context.get('finalAudience'),
        }
    else:
        fallback = build_fallback_persona_analysis(result, evidence, target_audience=target_audience)
        audience = fallback['audience']

    if not isinstance(ai_analysis, dict) or 'error' in ai_analysis:
        fallback = build_fallback_persona_analysis(result, evidence, target_audience=target_audience)
        return fallback

    regional_persona = ai_analysis.get('regionalPersona')
    persona_fit = ai_analysis.get('personaFit')

    if not isinstance(regional_persona, dict):
        fallback = build_fallback_persona_analysis(result, evidence, target_audience=target_audience)
        regional_persona = fallback['regionalPersona']
    if not isinstance(persona_fit, dict):
        fallback = build_fallback_persona_analysis(result, evidence, target_audience=target_audience)
        persona_fit = fallback['personaFit']

    fallback = build_fallback_persona_analysis(result, evidence, target_audience=target_audience)
    return {
        'audience': audience,
        'regionalPersona': regional_persona,
        'personaFit': {
            'score': persona_fit.get('score', fallback['personaFit'].get('score')),
            'isFit': persona_fit.get('isFit', fallback['personaFit'].get('isFit')),
            'matchingSignals': persona_fit.get('matchingSignals', fallback['personaFit'].get('matchingSignals', [])),
            'mismatchSignals': persona_fit.get('mismatchSignals', fallback['personaFit'].get('mismatchSignals', [])),
            'summary': persona_fit.get('summary', fallback['personaFit'].get('summary')),
        },
    }


def create_persona_context(target_audience_result):
    """Create a structured persona context for analysis focus."""
    if not target_audience_result:
        return None

    source = target_audience_result.get('source', 'rule_based')
    final_audience = target_audience_result.get('finalAudience', '')

    persona_focus = {
        'price_sensitive': False,
        'mobile_first': False,
        'local_trust': False,
    }

    audience_lower = final_audience.lower() if final_audience else ''

    if any(kw in audience_lower for kw in ['价格', '便宜', '优惠', 'discount', 'save', 'value', '性价比']):
        persona_focus['price_sensitive'] = True

    if any(kw in audience_lower for kw in ['手机', '移动', 'mobile', 'app', '快速', 'quick']):
        persona_focus['mobile_first'] = True

    if any(kw in audience_lower for kw in ['本地', '当地', '信任', 'review', '评价', '保障']):
        persona_focus['local_trust'] = True

    return {
        'source': source,
        'finalAudience': final_audience,
        'focusAreas': persona_focus,
    }
