"""Careers sites built on Phenom (pages like https://<host>/global/en/search-results), e.g. G42.
Uses the 'widgets' JSON endpoint the careers page itself calls."""

import time

from common import country_code, fetch_json, html_to_text

PAGE_SIZE = 50


class PhenomSource:
    """Config: base_url (e.g. "https://careers.g42.ai"), locale path (e.g. "global/en"), lang ("en_global"), country ("global")."""

    def __init__(self, cfg):
        self.base = cfg["base_url"].rstrip("/")
        self.path = cfg.get("path", "global/en").strip("/")
        self.lang = cfg.get("lang", "en_global")
        self.country = cfg.get("country", "global")
        self.brand_as_company = cfg.get("brand_as_company", False)
        self.company = cfg["company"]

    def _widgets(self, payload):
        base = {"lang": self.lang, "deviceType": "desktop", "country": self.country, "siteType": "external"}
        return fetch_json(f"{self.base}/widgets", data={**base, **payload})

    def fetch(self):
        offset, total = 0, None
        while total is None or offset < total:
            data = self._widgets({"pageName": "search-results", "ddoKey": "refineSearch", "from": offset, "size": PAGE_SIZE,
                                  "jobs": True, "counts": False, "keywords": "", "global": True, "selected_fields": {},
                                  "sortBy": "", "subsearch": "", "clearAll": False, "jdsource": "facets",
                                  "isSliderEnable": False, "locationData": {}})
            block = data.get("refineSearch") or {}
            total = block.get("totalHits") or 0
            jobs = (block.get("data") or {}).get("jobs") or []
            if not jobs:
                break
            for j in jobs:
                yield self._posting(j)
            offset += len(jobs)
            time.sleep(0.3)

    def _posting(self, j):
        locations = j.get("multi_location") or [j.get("location") or j.get("cityStateCountry")]
        locations = [l for l in locations if l]
        codes = [country_code(l) for l in locations] or [country_code(j.get("country"))]
        teaser = ((j.get("ml_job_parser") or {}).get("descriptionTeaser") or "").strip()
        brand = j.get("brand") or j.get("businessUnit") or ""
        company = f"{self.company} · {brand}" if self.brand_as_company and brand and brand.lower() != self.company.lower() else None
        posting = {
            "key": str(j["jobId"]),
            "title": (j.get("title") or "").strip(),
            "locations": locations,
            "countries": [c for c in dict.fromkeys(codes) if c],
            "workplace_type": j.get("type") or "",
            "categories": [j.get("category"), j.get("department")] + list(j.get("multi_category") or []),
            "posted_date": j.get("postedDate") or "",
            "summary": teaser,
            "url": f"{self.base}/{self.path}/job/{j['jobId']}",
        }
        if company:
            posting["company"] = company
        return posting

    def details(self, posting):
        data = self._widgets({"pageName": "job", "ddoKey": "jobDetail", "jobId": posting["key"]})
        job = (((data.get("jobDetail") or {}).get("data") or {}).get("job")) or {}
        raw = job.get("description") or (job.get("structureData") or {}).get("description")
        return {"description": html_to_text(raw)}
