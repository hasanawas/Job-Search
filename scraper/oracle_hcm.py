"""Careers sites on Oracle HCM Candidate Experience
(URLs like https://<host>/hcmUI/CandidateExperience/en/sites/<site>/jobs), e.g. e& and Fortinet.
Uses the same public JSON API the careers page itself calls."""

import time
import urllib.parse

from common import country_code, fetch_json, html_to_text

PAGE_SIZE = 25
HEADERS = {"ora-irc-language": "en"}


class OracleHCMSource:
    def __init__(self, cfg):
        self.base = cfg["base_url"].rstrip("/")
        self.site = cfg["site_number"]
        self.lang = cfg.get("language", "en")

    def _api(self, resource, finder, extra=""):
        # Oracle's finder syntax uses literal ';' ',' '=' which must not be percent-encoded.
        return f"{self.base}/hcmRestApi/resources/latest/{resource}?onlyData=true{extra}&finder={finder}"

    def fetch(self):
        offset, total = 0, None
        while total is None or offset < total:
            finder = f"findReqs;siteNumber={self.site},limit={PAGE_SIZE},offset={offset},sortBy=POSTING_DATES_DESC"
            data = fetch_json(self._api("recruitingCEJobRequisitions", finder, "&expand=requisitionList.secondaryLocations"),
                              headers=HEADERS)
            items = data.get("items") or []
            if not items:
                break
            total = items[0].get("TotalJobsCount") or 0
            reqs = items[0].get("requisitionList") or []
            if not reqs:
                break
            for req in reqs:
                yield self._posting(req)
            offset += len(reqs)
            time.sleep(0.3)

    def _posting(self, req):
        locations = [req.get("PrimaryLocation")] + [l.get("Name") for l in req.get("secondaryLocations") or []]
        locations = list(dict.fromkeys(l for l in locations if l))
        codes = [req.get("PrimaryLocationCountry")] + [l.get("CountryCode") for l in req.get("secondaryLocations") or []]
        codes = [c.upper() for c in codes if c] or [country_code(l) for l in locations]
        return {
            "key": str(req["Id"]),
            "title": (req.get("Title") or "").strip(),
            "locations": locations,
            "countries": [c for c in dict.fromkeys(codes) if c],
            "workplace_type": req.get("WorkplaceType") or "",
            "categories": [req.get("JobFamily"), req.get("JobFunction"), req.get("Category")],
            "posted_date": req.get("PostedDate") or "",
            "summary": (req.get("ShortDescriptionStr") or "").strip(),
            "url": f"{self.base}/hcmUI/CandidateExperience/{self.lang}/sites/{self.site}/job/{req['Id']}",
        }

    def details(self, posting):
        finder = f"ById;Id=%22{urllib.parse.quote(posting['key'])}%22,siteNumber={self.site}"
        data = fetch_json(self._api("recruitingCEJobRequisitionDetails", finder, "&expand=all"), headers=HEADERS)
        d = (data.get("items") or [{}])[0]
        parts = []
        for heading, raw in [("", d.get("ExternalDescriptionStr")), ("Responsibilities", d.get("ExternalResponsibilitiesStr")),
                             ("Qualifications", d.get("ExternalQualificationsStr"))]:
            text = html_to_text(raw)
            if text:
                parts.append(f"{heading}\n{text}" if heading else text)
        return {"description": "\n\n".join(parts)}
