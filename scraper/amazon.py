"""Amazon jobs (https://www.amazon.jobs). Uses the search.json endpoint the search page itself calls,
one query per selected country."""

import json
import time
from datetime import datetime

from common import ISO3, country_code, fetch_json, html_to_text

API = "https://www.amazon.jobs/en/search.json"
PAGE_SIZE = 100


class AmazonSource:
    """Config: countries (ISO codes; filled from defaults when not set)."""

    def __init__(self, cfg):
        self.countries = [c.upper() for c in cfg.get("countries", [])]

    def fetch(self):
        seen = set()
        for code in self.countries:
            iso3 = ISO3.get(code)
            if not iso3:
                continue
            offset, total = 0, None
            while total is None or offset < total:
                data = fetch_json(f"{API}?normalized_country_code%5B%5D={iso3}&result_limit={PAGE_SIZE}&offset={offset}&sort=recent")
                total = data.get("hits") or 0
                jobs = data.get("jobs") or []
                if not jobs:
                    break
                for j in jobs:
                    if j.get("id") not in seen:
                        seen.add(j.get("id"))
                        yield self._posting(j)
                offset += len(jobs)
                time.sleep(0.3)

    def _posting(self, j):
        locations, codes = [], []
        for raw in j.get("locations") or []:
            try:
                loc = json.loads(raw) if isinstance(raw, str) else raw
            except ValueError:
                continue
            name = ", ".join(x for x in [loc.get("normalizedCityName") or loc.get("city"), loc.get("normalizedCountryName")] if x)
            if name:
                locations.append(name)
            codes.append((loc.get("countryIso2a") or "").upper() or country_code(loc.get("normalizedCountryName")))
        if not locations and j.get("normalized_location"):
            locations = [j["normalized_location"]]
        try:
            posted = datetime.strptime(" ".join((j.get("posted_date") or "").split()), "%B %d, %Y").date().isoformat()
        except ValueError:
            posted = ""
        parts = [("", j.get("description")), ("Basic qualifications", j.get("basic_qualifications")),
                 ("Preferred qualifications", j.get("preferred_qualifications"))]
        description = "\n\n".join(f"{h}\n{html_to_text(t)}".strip() for h, t in parts if html_to_text(t))
        return {
            "key": str(j.get("id_icims") or j.get("id")),
            "title": (j.get("title") or "").strip(),
            "locations": locations,
            "countries": [c for c in dict.fromkeys(codes) if c],
            "workplace_type": "",
            "categories": [j.get("job_category"), j.get("job_family")],
            "posted_date": posted,
            "summary": html_to_text(j.get("description_short"))[:300],
            "url": f"https://www.amazon.jobs{j.get('job_path') or ''}",
            "description": description,
        }
