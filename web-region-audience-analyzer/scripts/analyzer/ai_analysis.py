"""
ai_analysis.py — AI API caller and content analysis.
"""
import json
import re
import urllib.request


def _call_ai_api(messages, api_base, api_key, model='gpt-4o',
                 temperature=0.3, timeout=60):
    api_url = api_base.rstrip('/') + '/chat/completions'

    payload = {
        'model': model,
        'messages': messages,
        'temperature': temperature,
        'response_format': {'type': 'json_object'},
    }

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}',
    }

    body = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(api_url, data=body, headers=headers, method='POST')

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            return data['choices'][0]['message']['content']
    except Exception as e:
        return {'error': str(e)}


AI_CONTENT_ANALYSIS_PROMPT = """\
You are an expert in cross-border e-commerce localization and multilingual content quality analysis.

Analyze the following web page content and provide a structured assessment.

## Context
- **Page URL**: {url}
- **Detected Region**: {region} ({region_name})
- **Detected Language**: {language} ({language_name})
- **Region Confidence**: {confidence}
- **User-Provided Target Audience**: {target_audience}

## Page Content (truncated to first 3000 chars):
```
{content}
```

## Your Task

Analyze the content and return a JSON object with EXACTLY this structure:

{{
  "targetAudience": {{
    "inferredAudience": "Who this website appears to target based on content and value proposition",
    "finalAudience": "Use user-provided target audience if present, otherwise use inferredAudience"
  }},
  "regionalPersona": {{
    "regionCode": "{region}",
    "regionName": "{region_name}",
    "language": "{language_name}",
    "personaLabel": "One-sentence persona label for this region + audience",
    "traits": ["Trait 1", "Trait 2", "Trait 3"],
    "motivations": ["Motivation 1", "Motivation 2"],
    "painPoints": ["Pain point 1", "Pain point 2"],
    "purchaseDrivers": ["Driver 1", "Driver 2", "Driver 3"]
  }},
  "personaFit": {{
    "score": <1-10 float, 10=website perfectly matches this persona>,
    "isFit": <true/false>,
    "matchingSignals": ["Signals that match persona needs"],
    "mismatchSignals": ["Signals that do not match persona needs"],
    "summary": "Concise summary of fit between website and persona"
  }},
  "inferredProductType": "Brief description of what this website/page is about (e.g., 'Fashion e-commerce', 'SaaS project management tool', 'News portal')",
  "languageQuality": {{
    "score": <1-10 float, 10=perfect native quality>,
    "isNativeLevel": <true/false>,
    "machineTranslationDetected": <true/false>,
    "details": "Explain your assessment: grammar quality, naturalness, vocabulary appropriateness for the target region"
  }},
  "regionFit": {{
    "score": <1-10 float, 10=perfectly adapted for target region>,
    "culturallyApproriate": <true/false>,
    "issues": ["List specific issues, e.g., 'Uses US date format MM/DD for German audience', 'Mentions Thanksgiving sale for Japanese market'"],
    "strengths": ["List what's done well, e.g., 'Uses local currency correctly', 'References local holidays'"]
  }},
  "contentProductAlignment": {{
    "score": <1-10 float, 10=content perfectly matches product positioning>,
    "details": "Does the copy, tone, and messaging match what the product/service is? Is the value proposition clear for the target audience?"
  }},
  "suggestions": [
    "Actionable suggestion 1 for improving localization quality",
    "Actionable suggestion 2...",
    "..."
  ]
}}

IMPORTANT:
- Respond ONLY with valid JSON, no markdown wrapping.
- If the content is too short to assess, still provide your best estimate and note the limitation.
- Focus on whether the content feels natural to a native speaker of the target region.
- Check for: machine translation artifacts, cultural mismatches, inappropriate idioms, wrong date/number formats, missing local context.
"""


def analyze_content_with_ai(text_content, url, result, api_base, api_key,
                             model='gpt-4o', timeout=60, target_audience=None):
    from .persona import resolve_target_audience

    if not text_content or len(text_content.strip()) < 20:
        return {'error': 'Insufficient text content for AI analysis'}

    region = result.get('primaryRegion', 'Unknown')
    region_name = result.get('primaryRegionName', 'Unknown')
    language = result.get('primaryLanguage', 'Unknown')
    language_name = result.get('primaryLanguageName', 'Unknown')
    confidence = result.get('regionConfidence', 0)

    prompt = AI_CONTENT_ANALYSIS_PROMPT.format(
        url=url,
        region=region,
        region_name=region_name,
        language=language,
        language_name=language_name,
        confidence=confidence,
        target_audience=(target_audience.strip() if isinstance(target_audience, str) and target_audience.strip() else 'Not provided'),
        content=text_content[:3000],
    )

    messages = [
        {'role': 'system', 'content': 'You are a multilingual content quality analyst. Always respond with valid JSON.'},
        {'role': 'user', 'content': prompt},
    ]

    raw_reply = _call_ai_api(messages, api_base, api_key, model=model, timeout=timeout)

    if isinstance(raw_reply, dict) and 'error' in raw_reply:
        return raw_reply

    try:
        analysis = json.loads(raw_reply)
        analysis['targetAudience'] = resolve_target_audience(
            target_audience, result, ai_analysis=analysis
        )
        return analysis
    except json.JSONDecodeError:
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw_reply, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        return {'error': 'Failed to parse AI response as JSON', 'rawReply': raw_reply[:500]}
