"""Shared helpers: HTTP with retries, HTML-to-text, and country names."""

import html
import json
import re
import time
import urllib.error
import urllib.request
from datetime import date, timedelta
from html.parser import HTMLParser

USER_AGENT = "Mozilla/5.0 (compatible; IT-Job-Portal/1.0; +https://github.com/hasanawas/Job-Search)"


def fetch_json(url, data=None, headers=None, retries=3, timeout=60):
    """GET (or POST when `data` is given, sent as JSON) and parse the JSON reply."""
    h = {"User-Agent": USER_AGENT, "Accept": "application/json", "Accept-Language": "en-US,en"}
    body = None
    if data is not None:
        body = json.dumps(data).encode()
        h["Content-Type"] = "application/json"
    h.update(headers or {})
    last_error = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, data=body, headers=h)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as e:
            last_error = e
            if e.code in (400, 401, 403, 404):
                break  # retrying won't help
        except Exception as e:  # network errors, bad JSON
            last_error = e
        time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"{'POST' if data is not None else 'GET'} {url} failed: {last_error}")


class _TextExtractor(HTMLParser):
    BLOCK_TAGS = {"p", "div", "br", "li", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6", "tr"}

    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag == "li":
            self.parts.append("\n• ")
        elif tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self.BLOCK_TAGS and tag != "li":
            self.parts.append("\n")

    def handle_data(self, data):
        self.parts.append(data)


def html_to_text(raw):
    """Turn a posting's HTML description into plain text (the site never renders scraped HTML)."""
    if not raw:
        return ""
    parser = _TextExtractor()
    parser.feed(raw)
    text = html.unescape("".join(parser.parts)).replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def relative_posted_date(text, today=None):
    """Workday says 'Posted Today', 'Posted Yesterday', 'Posted 3 Days Ago', 'Posted 30+ Days Ago'."""
    today = today or date.today()
    t = (text or "").lower()
    if "today" in t:
        days = 0
    elif "yesterday" in t:
        days = 1
    else:
        m = re.search(r"(\d+)", t)
        if not m:
            return ""
        days = int(m.group(1))
    return (today - timedelta(days=days)).isoformat()


COUNTRIES = {
    "AE": "United Arab Emirates", "SA": "Saudi Arabia", "QA": "Qatar", "KW": "Kuwait", "BH": "Bahrain", "OM": "Oman",
    "EG": "Egypt", "JO": "Jordan", "LB": "Lebanon", "MA": "Morocco", "TR": "Türkiye", "IL": "Israel", "PK": "Pakistan",
    "LK": "Sri Lanka", "IN": "India", "BD": "Bangladesh", "NP": "Nepal", "MV": "Maldives",
    "SG": "Singapore", "MY": "Malaysia", "ID": "Indonesia", "TH": "Thailand", "VN": "Vietnam", "PH": "Philippines",
    "CN": "China", "HK": "Hong Kong", "TW": "Taiwan", "JP": "Japan", "KR": "South Korea", "AU": "Australia", "NZ": "New Zealand",
    "GB": "United Kingdom", "IE": "Ireland", "FR": "France", "DE": "Germany", "NL": "Netherlands", "BE": "Belgium",
    "LU": "Luxembourg", "CH": "Switzerland", "AT": "Austria", "IT": "Italy", "ES": "Spain", "PT": "Portugal",
    "SE": "Sweden", "NO": "Norway", "DK": "Denmark", "FI": "Finland", "PL": "Poland", "CZ": "Czech Republic",
    "SK": "Slovakia", "HU": "Hungary", "RO": "Romania", "BG": "Bulgaria", "GR": "Greece", "RS": "Serbia",
    "LT": "Lithuania", "LV": "Latvia", "EE": "Estonia", "UA": "Ukraine", "ZA": "South Africa", "NG": "Nigeria",
    "KE": "Kenya", "MU": "Mauritius", "US": "United States", "CA": "Canada", "MX": "Mexico", "BR": "Brazil",
    "AR": "Argentina", "CL": "Chile", "CO": "Colombia", "CR": "Costa Rica", "PE": "Peru", "PR": "Puerto Rico",
}
_ALIASES = {
    "uae": "AE", "u.a.e": "AE", "dubai": "AE", "abu dhabi": "AE", "sharjah": "AE", "ajman": "AE", "ras al khaimah": "AE",
    "fujairah": "AE", "al ain": "AE", "riyadh": "SA", "jeddah": "SA", "ksa": "SA", "doha": "QA", "manama": "BH",
    "muscat": "OM", "colombo": "LK", "united states of america": "US", "usa": "US", "uk": "GB", "england": "GB",
    "china/mainland": "CN", "china/hong kong sar": "HK", "turkey": "TR", "czechia": "CZ",
}
_NAME_TO_CODE = {v.lower(): k for k, v in COUNTRIES.items()}
_NAME_TO_CODE.update(_ALIASES)


def country_name(code):
    return COUNTRIES.get((code or "").upper(), (code or "").upper())


def country_code(text):
    """Best-effort ISO code from a country name, code or location string ('Dubai, United Arab Emirates')."""
    if not text:
        return ""
    t = text.strip().lower()
    if t in _NAME_TO_CODE:
        return _NAME_TO_CODE[t]
    if len(t) == 2 and t.upper() in COUNTRIES:
        return t.upper()
    # Longest names first so 'United Arab Emirates' wins over shorter partial matches.
    for name in sorted(_NAME_TO_CODE, key=len, reverse=True):
        if re.search(r"(?<![a-z])" + re.escape(name) + r"(?![a-z])", t):
            return _NAME_TO_CODE[name]
    return ""
