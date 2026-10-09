"""Michael Page job listings (https://www.michaelpage.ae/jobs/<category>/<country>), a recruiter whose
clients are usually unnamed. Reads the listing page tiles and each new job's page for its full advert."""

import html
import json
import re
import time

from common import country_code, fetch_text, html_to_text

MAX_PAGES = 20


class MichaelPageSource:
    """Config: base_url (e.g. "https://www.michaelpage.ae"), list_path (e.g. "/jobs/technology/united-arab-emirates"),
    country (ISO code used when a tile's location names only a city we don't know)."""

    def __init__(self, cfg):
        self.base = cfg["base_url"].rstrip("/")
        self.list_path = cfg["list_path"]
        self.default_country = (cfg.get("country") or "").upper()

    def fetch(self):
        url, seen = f"{self.base}{self.list_path}", set()
        for _ in range(MAX_PAGES):
            page = fetch_text(url)
            tiles = re.findall(r'<li class="views-row">(.*?)</li>\s*(?=<li class="views-row">|</ul>)', page, re.S)
            fresh = 0
            for tile in tiles:
                p = self._posting(tile)
                if p and p["key"] not in seen:
                    seen.add(p["key"])
                    fresh += 1
                    yield p
            nxt = re.search(r'<a[^>]+href="([^"]+)"[^>]*rel="next"', page) or re.search(r'pager__item--next[^>]*>\s*<a[^>]+href="([^"]+)"', page)
            if not fresh or not nxt:
                break
            url = html.unescape(nxt.group(1))
            url = url if url.startswith("http") else f"{self.base}{url if url.startswith('/') else self.list_path + url}"
            time.sleep(0.5)

    def _posting(self, tile):
        link = re.search(r'<h3>\s*<a href="(/job-detail/[^"]+)"[^>]*>(.*?)</a>', tile, re.S)
        if not link:
            return None
        text = lambda cls: html.unescape(re.sub(r"<[^>]+>", " ", (re.search(rf'<div class="{cls}">(.*?)</div>', tile, re.S) or [None, ""])[1])).split()  # noqa: E731
        location = " ".join(text("job-location"))
        code = country_code(location) or self.default_country
        place = ", ".join(x for x in [location, "United Arab Emirates" if code == "AE" and "emirates" not in location.lower() else ""] if x)
        summary = html_to_text((re.search(r'<div class="job_advert__job-summary-text">(.*?)</div>', tile, re.S) or [None, ""])[1])
        return {
            "key": link.group(1).rstrip("/").rsplit("/", 1)[-1],
            "title": html.unescape(re.sub(r"<[^>]+>", "", link.group(2))).strip(),
            "locations": [place] if place else [],
            "countries": [code] if code else [],
            "workplace_type": "",
            "categories": [],
            "posted_date": "",
            "summary": summary[:300],
            "url": f"{self.base}{link.group(1)}",
        }

    def details(self, posting):
        page = fetch_text(posting["url"])
        m = re.search(r'<script type="application/ld\+json">\s*(\{.*?"JobPosting".*?\})\s*</script>', page, re.S)
        if not m:
            return {}
        try:
            data = json.loads(m.group(1), strict=False)
        except ValueError:
            return {}
        return {"description": html_to_text(data.get("description")), "posted_date": (data.get("datePosted") or "")[:10]}
