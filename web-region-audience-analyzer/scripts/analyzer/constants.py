"""
constants.py — All mappings and lookup tables.
No imports needed (pure data).
"""

TLD_MAP = {
    '.cn': 'CN', '.de': 'DE', '.jp': 'JP', '.uk': 'GB', '.fr': 'FR', '.ru': 'RU',
    '.br': 'BR', '.in': 'IN', '.kr': 'KR', '.au': 'AU', '.ca': 'CA', '.it': 'IT',
    '.es': 'ES', '.nl': 'NL', '.se': 'SE', '.no': 'NO', '.dk': 'DK', '.fi': 'FI',
    '.pl': 'PL', '.tr': 'TR', '.id': 'ID', '.vn': 'VN', '.th': 'TH', '.my': 'MY',
    '.sg': 'SG', '.ph': 'PH', '.mx': 'MX', '.ar': 'AR', '.cl': 'CL', '.co': 'CO',
    '.za': 'ZA', '.eg': 'EG', '.sa': 'SA', '.ae': 'AE', '.il': 'IL', '.nz': 'NZ',
    '.ie': 'IE', '.ch': 'CH', '.at': 'AT', '.be': 'BE', '.pt': 'PT', '.gr': 'GR',
    '.cz': 'CZ', '.hu': 'HU', '.ro': 'RO', '.ua': 'UA', '.tw': 'TW', '.hk': 'HK',
}

LANG_TO_REGION = {
    'zh': 'CN', 'ja': 'JP', 'ko': 'KR', 'de': 'DE', 'fr': 'FR', 'ru': 'RU',
    'pt': 'BR', 'it': 'IT', 'es': 'ES', 'nl': 'NL', 'pl': 'PL', 'tr': 'TR',
    'vi': 'VN', 'th': 'TH', 'id': 'ID', 'ms': 'MY', 'tl': 'PH', 'ar': 'SA',
    'he': 'IL', 'hi': 'IN', 'bn': 'BD', 'uk': 'UA', 'cs': 'CZ', 'hu': 'HU',
    'ro': 'RO', 'el': 'GR', 'sv': 'SE', 'no': 'NO', 'da': 'DK', 'fi': 'FI',
    'fa': 'IR', 'sw': 'KE',
    # English intentionally excluded -- too global to map to one country
}

COUNTRY_NAMES = {
    'CN': 'China', 'US': 'United States', 'DE': 'Germany', 'JP': 'Japan',
    'GB': 'United Kingdom', 'FR': 'France', 'RU': 'Russia', 'BR': 'Brazil',
    'IN': 'India', 'KR': 'South Korea', 'AU': 'Australia', 'CA': 'Canada',
    'IT': 'Italy', 'ES': 'Spain', 'NL': 'Netherlands', 'SE': 'Sweden',
    'NO': 'Norway', 'DK': 'Denmark', 'FI': 'Finland', 'PL': 'Poland',
    'TR': 'Turkey', 'ID': 'Indonesia', 'VN': 'Vietnam', 'TH': 'Thailand',
    'MY': 'Malaysia', 'SG': 'Singapore', 'PH': 'Philippines', 'MX': 'Mexico',
    'AR': 'Argentina', 'CL': 'Chile', 'CO': 'Colombia', 'ZA': 'South Africa',
    'EG': 'Egypt', 'SA': 'Saudi Arabia', 'AE': 'UAE', 'IL': 'Israel',
    'NZ': 'New Zealand', 'IE': 'Ireland', 'CH': 'Switzerland', 'AT': 'Austria',
    'BE': 'Belgium', 'PT': 'Portugal', 'GR': 'Greece', 'CZ': 'Czech Republic',
    'HU': 'Hungary', 'RO': 'Romania', 'UA': 'Ukraine', 'TW': 'Taiwan',
    'HK': 'Hong Kong', 'BD': 'Bangladesh', 'IR': 'Iran', 'KE': 'Kenya',
    'EU': 'European Union',
}

LANG_NAMES = {
    'en': 'English', 'zh': 'Chinese', 'zh-cn': 'Simplified Chinese',
    'zh-tw': 'Traditional Chinese', 'ja': 'Japanese', 'ko': 'Korean',
    'de': 'German', 'fr': 'French', 'es': 'Spanish', 'pt': 'Portuguese',
    'ru': 'Russian', 'ar': 'Arabic', 'hi': 'Hindi', 'it': 'Italian',
    'nl': 'Dutch', 'pl': 'Polish', 'tr': 'Turkish', 'vi': 'Vietnamese',
    'th': 'Thai', 'id': 'Indonesian', 'ms': 'Malay', 'sv': 'Swedish',
    'no': 'Norwegian', 'da': 'Danish', 'fi': 'Finnish', 'he': 'Hebrew',
    'uk': 'Ukrainian', 'cs': 'Czech', 'hu': 'Hungarian', 'ro': 'Romanian',
    'el': 'Greek', 'fa': 'Persian', 'bn': 'Bengali', 'tl': 'Filipino',
}

PHONE_PREFIXES = {
    r'\+1(?=[\s\-\.(])': 'US', r'\+44': 'GB', r'\+86': 'CN', r'\+81': 'JP',
    r'\+49': 'DE', r'\+33': 'FR', r'\+7(?=[\s\-\.(])': 'RU', r'\+55': 'BR',
    r'\+91': 'IN', r'\+82': 'KR', r'\+61': 'AU', r'\+39': 'IT', r'\+34': 'ES',
    r'\+31': 'NL', r'\+46': 'SE', r'\+47': 'NO', r'\+45': 'DK', r'\+358': 'FI',
    r'\+48': 'PL', r'\+90': 'TR', r'\+62': 'ID', r'\+84': 'VN', r'\+66': 'TH',
    r'\+60': 'MY', r'\+65': 'SG', r'\+63': 'PH', r'\+52': 'MX', r'\+54': 'AR',
    r'\+56': 'CL', r'\+57': 'CO', r'\+27': 'ZA', r'\+20': 'EG', r'\+966': 'SA',
    r'\+971': 'AE', r'\+972': 'IL',
}

CURRENCY_MAP = {
    'USD': 'US', 'EUR': 'EU', 'CNY': 'CN', 'RMB': 'CN', 'GBP': 'GB', 'JPY': 'JP',
    'INR': 'IN', 'RUB': 'RU', 'BRL': 'BR', 'KRW': 'KR', 'AUD': 'AU', 'CAD': 'CA',
    'CHF': 'CH', 'HKD': 'HK', 'SGD': 'SG', 'SEK': 'SE', 'NOK': 'NO', 'DKK': 'DK',
    'PLN': 'PL', 'TRY': 'TR', 'THB': 'TH', 'IDR': 'ID', 'MYR': 'MY', 'PHP': 'PH',
    'VND': 'VN', 'MXN': 'MX', 'ZAR': 'ZA', 'ILS': 'IL', 'SAR': 'SA', 'AED': 'AE',
}

CURRENCY_SYMBOLS = [
    (r'R\$', 'BRL'), (r'HK\$', 'HKD'), (r'S\$', 'SGD'), (r'Mex\$', 'MXN'),
    (r'(?<![A-Za-z])\$', 'USD'), (r'€', 'EUR'), (r'£', 'GBP'), (r'¥', 'CNY/JPY'),
    (r'₹', 'INR'), (r'₽', 'RUB'), (r'₩', 'KRW'), (r'zł', 'PLN'), (r'₺', 'TRY'),
    (r'฿', 'THB'), (r'₱', 'PHP'), (r'₫', 'VND'),
    (r'(?<!\w)Rp(?:\s|\.)', 'IDR'), (r'(?<!\w)RM(?:\s|\.|\\d)', 'MYR'),
    (r'(?<![A-Za-z])kr(?:\s|\.|,|\d)', 'SEK/NOK/DKK'),
]

SOCIAL_MEDIA_DOMAINS = {
    'weixin.qq.com': 'CN', 'weibo.com': 'CN', 'douyin.com': 'CN',
    'bilibili.com': 'CN', 'zhihu.com': 'CN', 'baidu.com': 'CN',
    'vk.com': 'RU', 'ok.ru': 'RU', 'mail.ru': 'RU',
    'line.me': 'JP', 'nicovideo.jp': 'JP', 'ameblo.jp': 'JP',
    'kakaotalk.com': 'KR', 'naver.com': 'KR', 'daum.net': 'KR',
}

PAYMENT_METHODS = {
    'NL': ['iDEAL'],
    'DE': ['Sofort', 'Giropay', 'Klarna', 'SEPA', 'Rechnung'],
    'AT': ['EPS'],
    'PL': ['BLIK', 'Przelewy24'],
    'BR': ['Pix', 'Boleto'],
    'BE': ['Bancontact'],
    'CN': ['Alipay', 'WeChat Pay', 'UnionPay'],
    'JP': ['Konbini', 'JCB', 'PayPay'],
    'RU': ['Mir', 'Yandex'],
    'IN': ['UPI', 'RuPay', 'Paytm'],
    'SE': ['Swish'],
    'CH': ['TWINT'],
}

SPELLING_VARIANTS = {
    'US': [r'\bcolor\b', r'\bflavor\b', r'\bcenter\b', r'\bmeter\b', r'\blicense\b', r'\bshipping\b'],
    'UK': [r'\bcolour\b', r'\bflavour\b', r'\bcentre\b', r'\bmetre\b', r'\blicence\b', r'\bdelivery\b'],
}

MEASUREMENT_UNITS = {
    'Imperial': [r'\binch(?:es)?\b', r'\blbs?\b', r'\boz\b', r'\bfeet\b', r'\byards?\b'],
    'Metric': [r'\bcm\b', r'\bkg\b', r'\bml\b', r'\bmeters?\b', r'\bliters?\b'],
}
