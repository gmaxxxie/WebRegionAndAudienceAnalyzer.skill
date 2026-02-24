"""
fetcher.py — HTTP fetching with dual SSL strategy.
"""
import re
import ssl
import urllib.request
import urllib.parse


def fetch_html(url, timeout=15):
    """Try multiple SSL strategies for resilient fetching."""
    headers = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }

    strategies = [
        lambda: ssl.create_default_context(),
        lambda: _permissive_ssl_context(),
    ]

    last_error = None
    for make_ctx in strategies:
        try:
            ctx = make_ctx()
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                raw = resp.read()
                charset = 'utf-8'
                ct = resp.headers.get('Content-Type', '')
                m = re.search(r'charset=([^\s;]+)', ct, re.IGNORECASE)
                if m:
                    charset = m.group(1)
                try:
                    html = raw.decode(charset, errors='replace')
                except (LookupError, UnicodeDecodeError):
                    html = raw.decode('utf-8', errors='replace')
                return html, resp.geturl(), None
        except Exception as e:
            last_error = e
            continue

    return None, None, str(last_error)


def _permissive_ssl_context():
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        ctx.set_ciphers('DEFAULT:@SECLEVEL=1')
    except ssl.SSLError:
        ctx.set_ciphers('DEFAULT')
    return ctx
