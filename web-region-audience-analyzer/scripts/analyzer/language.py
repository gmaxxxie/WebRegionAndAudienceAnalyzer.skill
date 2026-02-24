"""
language.py — Language detection (NLP Cloud + offline langdetect).
"""
import json
import urllib.request

try:
    from langdetect import detect_langs, DetectorFactory
    DetectorFactory.seed = 0
    HAS_LANGDETECT = True
except ImportError:
    HAS_LANGDETECT = False


def detect_language_nlpcloud(text, token):
    api_url = "https://api.nlpcloud.io/v1/gpu/lang-detect"
    headers = {
        "Authorization": f"Token {token}",
        "Content-Type": "application/json",
    }
    body = json.dumps({"text": text[:5000]}).encode('utf-8')
    req = urllib.request.Request(api_url, data=body, headers=headers, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        return {'error': str(e)}


def detect_language_offline(text):
    if not HAS_LANGDETECT:
        return {'error': 'langdetect not installed (pip install langdetect)'}
    if not text or len(text.strip()) < 10:
        return {'error': 'Insufficient text for language detection'}
    try:
        langs = detect_langs(text[:5000])
        return {'results': [{'lang': str(l.lang), 'confidence': round(l.prob, 6)} for l in langs]}
    except Exception as e:
        return {'error': str(e)}
