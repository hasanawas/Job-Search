"""Careers sites on Jibe / iCIMS Attract (pages like https://careers.<company>/jobs), e.g. M42.
Uses the /api/jobs JSON endpoint the careers page itself calls."""

import time

from common import country_code, fetch_json, html_to_text


class JibeSource:
    """Config: base_url (e.g. "https://careers.m42.ae")."""

    def __init__(self, cfg):
        self.base = cfg["base_url"].rstrip("/")

    def fetch(self):
        page, seen, total = 1, 0, None
        while total is None or seen < total:
            data = fetch_json(f"{self.base}/api/jobs?page={page}&sortBy=posted_date&descending=true&internal=false")
            total = data.get("totalCount") or 0
            jobs = data.get("jobs") or []
            if not jobs:
                break
            for j in jobs:
                yield self._posting(j.get("data") or {})
            seen += len(jobs)
            page += 1
            time.sleep(0.3)

    def _posting(self, j):
        country = j.get("country") or next(iter(j.get("tags3") or []), "")
        city = j.get("city") or next(iter(j.get("tags2") or []), "")
        place = ", ".join(x for x in [city, country] if x)
        parts = [html_to_text(j.get(k)) for k in ("description", "responsibilities", "qualifications")]
        return {
            "key": str(j.get("slug") or j.get("req_id")),
            "title": (j.get("title") or "").strip(),
            "locations": [place] if place else [],
            "countries": [c for c in [country_code(country or place)] if c],
            "workplace_type": "",
            "categories": [c.get("name") for c in j.get("categories") or []] + [j.get("department")],
            "posted_date": (j.get("posted_date") or "")[:10],
            "summary": "",
            "url": f"{self.base}/jobs/{j.get('slug') or j.get('req_id')}",
            "description": "\n\n".join(p for p in parts if p),
        }
