"""
aggregation.py — Site-level result aggregation across multiple pages.
"""
from .constants import COUNTRY_NAMES, LANG_NAMES


def aggregate_site_results(page_results):
    if not page_results:
        return None

    all_scores = {}
    lang_counts = {}
    region_counts = {}

    for pr in page_results:
        result = pr.get('result')
        if not result:
            continue

        breakdown = result.get('signalBreakdown', {})
        for region, score in breakdown.items():
            all_scores[region] = all_scores.get(region, 0) + score

        pr_region = result.get('primaryRegion')
        pr_lang = result.get('primaryLanguage')
        if pr_region:
            region_counts[pr_region] = region_counts.get(pr_region, 0) + 1
        if pr_lang:
            lang_counts[pr_lang] = lang_counts.get(pr_lang, 0) + 1

    if all_scores:
        primary_region = max(all_scores, key=lambda k: all_scores[k])
    else:
        primary_region = None

    if lang_counts:
        primary_lang = max(lang_counts, key=lambda k: lang_counts[k])
    else:
        primary_lang = None

    num_pages = len([pr for pr in page_results if pr.get('result')])
    if primary_region and num_pages > 0:
        agree_count = region_counts.get(primary_region, 0)
        consistency = round(agree_count / num_pages, 2)
    else:
        consistency = 0.0

    confidences = [
        pr['result']['regionConfidence']
        for pr in page_results
        if pr.get('result') and pr['result'].get('regionConfidence') is not None
    ]
    avg_confidence = round(sum(confidences) / len(confidences), 2) if confidences else 0.0

    country_name = COUNTRY_NAMES.get(primary_region, primary_region) if primary_region else None
    lang_name = LANG_NAMES.get(primary_lang, primary_lang) if primary_lang else None

    if primary_region and primary_lang:
        audience = f"{lang_name}-speaking audience in {country_name}"
    elif primary_region:
        audience = f"Audience in {country_name}"
    else:
        audience = "Unknown"

    return {
        'primaryRegion': primary_region,
        'primaryRegionName': country_name,
        'primaryLanguage': primary_lang,
        'primaryLanguageName': lang_name,
        'likelyAudience': audience,
        'regionConfidence': avg_confidence,
        'regionConsistency': consistency,
        'pagesAnalyzed': num_pages,
        'regionDistribution': {
            k: round(v, 3)
            for k, v in sorted(all_scores.items(), key=lambda x: -x[1])
        },
        'languageDistribution': lang_counts,
    }


def aggregate_site_optimization(page_results):
    seen = set()
    all_recs = []

    for pr in page_results:
        opt = pr.get('optimization')
        if not opt:
            continue
        for rec in opt.get('recommendations', []):
            dedup_key = (rec['severity'], rec['category'], rec['issue'][:80])
            if dedup_key not in seen:
                seen.add(dedup_key)
                all_recs.append(rec)

    severity_order = {'critical': 0, 'warning': 1, 'info': 2}
    all_recs.sort(key=lambda r: severity_order.get(r['severity'], 9))

    critical_count = sum(1 for r in all_recs if r['severity'] == 'critical')
    warning_count = sum(1 for r in all_recs if r['severity'] == 'warning')
    info_count = sum(1 for r in all_recs if r['severity'] == 'info')

    score = 100
    score -= critical_count * 20
    score -= warning_count * 10
    score -= info_count * 2
    score = max(score, 0)

    if score >= 80:
        grade = 'A'
    elif score >= 60:
        grade = 'B'
    elif score >= 40:
        grade = 'C'
    elif score >= 20:
        grade = 'D'
    else:
        grade = 'F'

    return {
        'summary': {
            'score': score,
            'grade': grade,
            'totalIssues': len(all_recs),
            'critical': critical_count,
            'warnings': warning_count,
            'info': info_count,
        },
        'recommendations': all_recs,
    }


def aggregate_ai_analysis(page_ai_results):
    valid_results = [r for r in page_ai_results if r and 'error' not in r]
    if not valid_results:
        return {'error': 'No valid AI analysis results to aggregate'}

    lang_scores = [r['languageQuality']['score'] for r in valid_results
                   if 'languageQuality' in r and 'score' in r.get('languageQuality', {})]
    region_scores = [r['regionFit']['score'] for r in valid_results
                     if 'regionFit' in r and 'score' in r.get('regionFit', {})]
    alignment_scores = [r['contentProductAlignment']['score'] for r in valid_results
                        if 'contentProductAlignment' in r and 'score' in r.get('contentProductAlignment', {})]

    product_types = list(dict.fromkeys(
        r.get('inferredProductType', '') for r in valid_results
        if r.get('inferredProductType')
    ))

    mt_detected = any(
        r.get('languageQuality', {}).get('machineTranslationDetected', False)
        for r in valid_results
    )

    all_native = all(
        r.get('languageQuality', {}).get('isNativeLevel', False)
        for r in valid_results
    )

    all_issues = list(dict.fromkeys(
        issue
        for r in valid_results
        for issue in r.get('regionFit', {}).get('issues', [])
        if issue
    ))

    all_strengths = list(dict.fromkeys(
        s
        for r in valid_results
        for s in r.get('regionFit', {}).get('strengths', [])
        if s
    ))

    all_suggestions = list(dict.fromkeys(
        s
        for r in valid_results
        for s in r.get('suggestions', [])
        if s
    ))

    return {
        'inferredProductTypes': product_types,
        'pagesAnalyzed': len(valid_results),
        'languageQuality': {
            'averageScore': round(sum(lang_scores) / len(lang_scores), 1) if lang_scores else None,
            'isNativeLevel': all_native,
            'machineTranslationDetected': mt_detected,
        },
        'regionFit': {
            'averageScore': round(sum(region_scores) / len(region_scores), 1) if region_scores else None,
            'issues': all_issues[:20],
            'strengths': all_strengths[:20],
        },
        'contentProductAlignment': {
            'averageScore': round(sum(alignment_scores) / len(alignment_scores), 1) if alignment_scores else None,
        },
        'suggestions': all_suggestions[:20],
    }


def aggregate_persona_analysis(page_persona_results):
    valid = [p for p in page_persona_results if isinstance(p, dict)]
    if not valid:
        return None

    fit_scores = []
    audience_sources = []
    audience_values = []
    traits = []
    matching = []
    mismatching = []

    for item in valid:
        audience = item.get('audience', {})
        persona = item.get('regionalPersona', {})
        fit = item.get('personaFit', {})

        source = audience.get('source')
        if source:
            audience_sources.append(source)

        final_audience = audience.get('finalAudience')
        if final_audience:
            audience_values.append(final_audience)

        score = fit.get('score')
        if isinstance(score, (int, float)):
            fit_scores.append(float(score))

        traits.extend(persona.get('traits', []))
        matching.extend(fit.get('matchingSignals', []))
        mismatching.extend(fit.get('mismatchSignals', []))

    source = (
        'user_input' if 'user_input' in audience_sources
        else 'ai_inferred' if 'ai_inferred' in audience_sources
        else 'rule_based'
    )

    traits = list(dict.fromkeys([t for t in traits if t]))
    matching = list(dict.fromkeys([m for m in matching if m]))
    mismatching = list(dict.fromkeys([m for m in mismatching if m]))
    audience_values = list(dict.fromkeys([a for a in audience_values if a]))

    representative_persona = valid[0].get('regionalPersona', {})
    avg_score = round(sum(fit_scores) / len(fit_scores), 1) if fit_scores else None

    return {
        'audience': {
            'source': source,
            'userInput': None,
            'inferredAudience': audience_values[0] if audience_values else None,
            'finalAudience': audience_values[0] if audience_values else 'Unknown audience',
        },
        'regionalPersona': {
            'regionCode': representative_persona.get('regionCode'),
            'regionName': representative_persona.get('regionName'),
            'language': representative_persona.get('language'),
            'personaLabel': representative_persona.get('personaLabel'),
            'traits': traits[:10],
            'motivations': representative_persona.get('motivations', []),
            'painPoints': representative_persona.get('painPoints', []),
            'purchaseDrivers': representative_persona.get('purchaseDrivers', []),
        },
        'personaFit': {
            'score': avg_score,
            'isFit': bool(avg_score is not None and avg_score >= 7),
            'matchingSignals': matching[:20],
            'mismatchSignals': mismatching[:20],
            'summary': (
                "全站整体较符合目标 persona。"
                if avg_score is not None and avg_score >= 7
                else "全站与目标 persona 存在明显差距，建议优先修复关键本地化缺口。"
            ),
        },
    }
