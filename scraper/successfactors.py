"""Careers sites on SAP SuccessFactors Career Site Builder (pages like https://careers.<company>/go/<list>/<id>/),
e.g. EDGE Group. Reads the job list pages (25 jobs each) and each new job's page for its description."""

import html
import re
import time
from datetime import datetime

from common import country_code, country_name, fetch_text, html_to_text

PAGE_SIZE = 25


class SuccessFactorsSource:
    """Config: base_url, list_path (e.g. "/go/View-All-Jobs/4166222/"), country (ISO code used when a job
    names no country), facility_as_company (show the hiring entity, e.g. "EDGE · NIMR")."""

    def __init__(self, cfg):
        self.base = cfg["base_url"].rstrip("/")
        self.list_path = "/" + cfg["list_path"].strip("/") + "/"
        self.default_country = (cfg.get("country") or "").upper()
        self.facility_as_company = cfg.get("facility_as_company", False)
        self.company = cfg["company"]

    def fetch(self):
        offset, total = 0, None
        while total is None or offset < total:
            page = fetch_text(f"{self.base}{self.list_path}{offset if offset else ''}{'/' if offset else ''}")
            m = re.search(r'paginationLabel[^>]*>.*?of\s*<b>\s*([\d,]+)\s*</b>', page, re.S)
            total = int(m.group(1).replace(",", "")) if m else 0
            rows = re.findall(r'<tr class="data-row[^"]*">(.*?)</tr>', page, re.S)
            if not rows:
                break
            for row in rows:
                yield self._posting(row)
            offset += len(rows)
            time.sleep(0.5)

    def _posting(self, row):
        link = re.search(r'<a[^>]+href="(/job/[^"]+)"[^>]*class="jobTitle-link"[^>]*>(.*?)</a>', row, re.S) \
            or re.search(r'<a[^>]+class="jobTitle-link"[^>]+href="(/job/[^"]+)"[^>]*>(.*?)</a>', row, re.S)
        path, title = link.group(1), html.unescape(re.sub(r"<[^>]+>", "", link.group(2))).strip()
        cell = lambda cls: html.unescape(re.sub(r"<[^>]+>", "", (re.search(rf'<span class="{cls}"[^>]*>(.*?)</span>', row, re.S) or [None, ""])[1])).strip()  # noqa: E731
        facility, location = cell("jobFacility"), cell("jobLocation")
        # The job's URL starts with its city, e.g. /job/Abu-Dhabi-Sr_-Buyer-Abu/733481722/
        slug_place = path.split("/")[2].replace("-", " ")
        code = country_code(location) or country_code(slug_place) or self.default_country
        try:
            posted = datetime.strptime(cell("jobDate").replace("Sept", "Sep"), "%d %b %Y").date().isoformat()
        except ValueError:
            posted = ""
        posting = {
            "key": path.rstrip("/").rsplit("/", 1)[-1],
            "title": title,
            "locations": [location] if location else [],
            "countries": [code] if code else [],
            "workplace_type": "",
            "categories": [facility],
            "posted_date": posted,
            "summary": "",
            "url": f"{self.base}{path}",
        }
        if self.facility_as_company and facility:
            posting["company"] = f"{self.company} · {facility}"
        return posting

    def details(self, posting):
        page = fetch_text(posting["url"])
        m = re.search(r'<span class="jobdescription"[^>]*>(.*?)</span>\s*</div>', page, re.S) \
            or re.search(r'class="jobdescription"[^>]*>(.*?)</span>', page, re.S)
        out = {"description": html_to_text(m.group(1)) if m else ""}
        city = re.search(r'itemprop="addressLocality" content="([^"]*)"', page)
        country = re.search(r'itemprop="addressCountry" content="([^"]*)"', page)
        if city or country:
            parts = [city and city.group(1), country and country_name(country.group(1).strip())]
            place = ", ".join(x.strip() for x in parts if x and x.strip())
            if place:
                out["locations"] = [place]
        return out
