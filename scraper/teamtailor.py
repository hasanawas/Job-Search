"""Careers sites on Teamtailor (pages like https://careers.<company>/jobs), e.g. Astra Tech.
Uses the site's public jobs.rss feed, which lists every open job with its full description."""

import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

from common import country_code, fetch_text, html_to_text

TT = "{https://teamtailor.com/locations}"


class TeamtailorSource:
    """Config: base_url (e.g. "https://careers.astratech.ae")."""

    def __init__(self, cfg):
        self.base = cfg["base_url"].rstrip("/")

    def fetch(self):
        root = ET.fromstring(fetch_text(f"{self.base}/jobs.rss"))
        for item in root.iter("item"):
            yield self._posting(item)

    def _posting(self, item):
        text = lambda tag: (item.findtext(tag) or "").strip()  # noqa: E731
        locations, codes = [], []
        for loc in item.iter(f"{TT}location"):
            city, country = (loc.findtext(f"{TT}city") or "").strip(), (loc.findtext(f"{TT}country") or "").strip()
            name = ", ".join(x for x in [city or (loc.findtext(f"{TT}name") or "").strip(), country] if x)
            if name:
                locations.append(name)
            codes.append(country_code(country or name))
        link = text("link")
        remote = text("remoteStatus").lower()
        try:
            posted = parsedate_to_datetime(text("pubDate")).date().isoformat()
        except (TypeError, ValueError):
            posted = ""
        return {
            "key": link.rstrip("/").rsplit("/", 1)[-1].split("-", 1)[0] or text("guid"),
            "title": text("title"),
            "locations": locations,
            "countries": [c for c in dict.fromkeys(codes) if c],
            "workplace_type": {"fully": "Remote", "hybrid": "Hybrid"}.get(remote, ""),
            "categories": [text(f"{TT}department"), text(f"{TT}division"), text(f"{TT}role")],
            "posted_date": posted,
            "summary": "",
            "url": link,
            "description": html_to_text(text("description")),
        }
