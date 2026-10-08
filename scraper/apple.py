"""Apple jobs (https://jobs.apple.com). Reads the search results embedded in the search page,
one search per selected country (location slugs like 'united-arab-emirates-ARE')."""

import json
import re
import time

from common import ISO3, country_code, country_name, fetch_text

BASE = "https://jobs.apple.com"
MAX_PAGES = 30  # safety cap per country


class AppleSource:
    """Config: locale (default "en-ae"), countries (ISO codes; filled from defaults when not set)."""

    def __init__(self, cfg):
        self.locale = cfg.get("locale", "en-ae")
        self.countries = [c.upper() for c in cfg.get("countries", [])]

    def _page(self, slug, page):
        html = fetch_text(f"{BASE}/{self.locale}/search?location={slug}&page={page}")
        m = re.search(r'__staticRouterHydrationData = JSON\.parse\((".*?")\);', html, re.S)
        if not m:
            raise RuntimeError("Apple search page format changed: no hydration data")
        search = (json.loads(json.loads(m.group(1))).get("loaderData") or {}).get("search") or {}
        return search.get("searchResults") or [], search.get("totalRecords") or 0

    def fetch(self):
        seen = set()
        for code in self.countries:
            iso3 = ISO3.get(code)
            if not iso3:
                continue
            slug = re.sub(r"[^a-z]+", "-", country_name(code).lower()).strip("-") + f"-{iso3}"
            count = 0
            for page in range(1, MAX_PAGES + 1):
                results, total = self._page(slug, page)
                for r in results:
                    if r.get("positionId") not in seen:
                        seen.add(r.get("positionId"))
                        yield self._posting(r)
                count += len(results)
                if not results or count >= total:
                    break
                time.sleep(0.5)

    def _posting(self, r):
        locations, codes = [], []
        for loc in r.get("locations") or []:
            name = ", ".join(x for x in [loc.get("city"), loc.get("countryName")] if x)
            if name:
                locations.append(name)
            cid = loc.get("countryID") or ""
            iso3 = cid.rsplit("-", 1)[-1] if cid.startswith("iso-country-") else ""
            codes.append(next((k for k, v in ISO3.items() if v == iso3), "") or country_code(loc.get("countryName")))
        posted = (r.get("postDateInGMT") or "")[:10]
        slug = r.get("transformedPostingTitle") or ""
        return {
            "key": str(r.get("positionId") or r.get("id")),
            "title": (r.get("postingTitle") or "").strip(),
            "locations": locations,
            "countries": [c for c in dict.fromkeys(codes) if c],
            "workplace_type": "Remote" if r.get("homeOffice") else "",
            "categories": [(r.get("team") or {}).get("teamName")],
            "posted_date": posted,
            "summary": (r.get("jobSummary") or "")[:300],
            "url": f"{BASE}/{self.locale}/details/{r.get('positionId')}/{slug}",
            "description": (r.get("jobSummary") or "").strip(),
        }
