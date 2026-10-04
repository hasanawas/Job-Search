"""Careers sites on Workday (https://<tenant>.wdN.myworkdayjobs.com/<site> or
https://wdN.myworkdaysite.com/recruiting/<tenant>/<site>), e.g. Accenture and Sysco LABS.
Uses the JSON API the Workday careers page itself calls."""

import time

from common import country_code, fetch_json, html_to_text, relative_posted_date

PAGE_SIZE = 20  # Workday's maximum


class WorkdaySource:
    """Config:
      host:    e.g. "accenture.wd103.myworkdayjobs.com" or "wd5.myworkdaysite.com"
      tenant, site: from the careers URL
      countries: ISO codes; matched against Workday's own Country filter
      facets:  optional fixed filters, e.g. {"locations": ["<id>"]}; then set 'country' to the ISO code they cover
    """

    def __init__(self, cfg):
        self.host = cfg["host"]
        self.tenant = cfg["tenant"]
        self.site = cfg["site"]
        self.countries = [c.upper() for c in cfg.get("countries", [])]
        self.facets = cfg.get("facets")
        self.fixed_country = (cfg.get("country") or "").upper()
        self.api = f"https://{self.host}/wday/cxs/{self.tenant}/{self.site}"
        if "myworkdaysite.com" in self.host:
            self.public = f"https://{self.host}/en-US/recruiting/{self.tenant}/{self.site}"
        else:
            self.public = f"https://{self.host}/en-US/{self.site}"

    def _search(self, facets, offset):
        return fetch_json(f"{self.api}/jobs", data={"appliedFacets": facets, "limit": PAGE_SIZE, "offset": offset, "searchText": ""})

    def _country_facets(self):
        """Maps ISO code -> Workday's internal id for its Country filter."""
        data = self._search({}, 0)
        found = {}
        for facet in data.get("facets", []):
            groups = facet.get("values", []) if "values" in (facet.get("values") or [{}])[0] else [facet]
            for group in groups:
                if group.get("facetParameter") in ("locationCountry", "Location_Country"):
                    for v in group.get("values", []):
                        code = country_code(v.get("descriptor"))
                        if code:
                            found[code] = (group["facetParameter"], v["id"])
        return found

    def _queries(self):
        if self.facets:
            yield self.fixed_country, self.facets
            return
        if not self.countries:
            yield "", {}
            return
        available = self._country_facets()
        for code in self.countries:
            if code in available:
                param, fid = available[code]
                yield code, {param: [fid]}

    def fetch(self):
        for code, facets in self._queries():
            offset, total = 0, None
            while total is None or offset < total:
                data = self._search(facets, offset)
                if total is None:
                    total = data.get("total") or 0
                items = data.get("jobPostings") or []
                if not items:
                    break
                for p in items:
                    if p.get("externalPath"):
                        yield self._posting(p, code)
                offset += len(items)
                time.sleep(0.3)

    def _posting(self, p, code):
        path = p["externalPath"]
        loc = p.get("locationsText") or ""
        return {
            "key": path.rsplit("_", 1)[-1] if "_" in path else path,
            "path": path,
            "title": (p.get("title") or "").strip(),
            "locations": [loc] if loc and "Locations" not in loc else [],
            "countries": [code] if code else [],
            "workplace_type": "",
            "categories": [],
            "posted_date": relative_posted_date(p.get("postedOn")),
            "summary": "",
            "url": self.public + path,
        }

    def details(self, posting):
        d = fetch_json(self.api + posting["path"]).get("jobPostingInfo") or {}
        out = {"description": html_to_text(d.get("jobDescription"))}
        if d.get("startDate"):
            out["posted_date"] = d["startDate"]
        locs = [d.get("location")] + list(d.get("additionalLocations") or [])
        locs = [l for l in locs if l]
        if locs:
            out["locations"] = locs
        if d.get("externalUrl"):
            out["url"] = d["externalUrl"]
        return out
