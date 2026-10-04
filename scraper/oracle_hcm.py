"""Scraper for careers sites built on Oracle HCM Candidate Experience
(URLs like https://<host>/hcmUI/CandidateExperience/en/sites/<site>/jobs).

Uses the same public JSON API the careers page itself calls, so no HTML parsing."""

import html
import json
import re
import time
import urllib.parse
import urllib.request
from html.parser import HTMLParser

PAGE_SIZE = 25
USER_AGENT = "Mozilla/5.0 (compatible; IT-Job-Portal/1.0; +https://github.com/hasanawas/Job-Search)"
HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/json",
    "Accept-Language": "en",
    "ora-irc-language": "en",
}

# Country names used as a fallback when a posting has no country code.
COUNTRY_NAMES = {
    "AE": ["united arab emirates", "uae", "dubai", "abu dhabi", "sharjah", "ajman", "ras al khaimah", "fujairah", "al ain"],
}


def _get_json(url, retries=3):
    last_error = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.load(resp)
        except Exception as e:  # network errors, HTTP 5xx, bad JSON
            last_error = e
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"GET {url} failed: {last_error}")


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
    """Turn the posting's HTML description into plain text (the site never renders scraped HTML)."""
    if not raw:
        return ""
    parser = _TextExtractor()
    parser.feed(raw)
    text = html.unescape("".join(parser.parts)).replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


class OracleHCMSource:
    def __init__(self, source):
        self.source = source
        self.base = source["base_url"].rstrip("/")
        self.site = source["site_number"]
        self.lang = source.get("language", "en")
        self.countries = {c.upper() for c in source.get("countries", [])}

    def _api(self, resource, finder, extra=""):
        # Oracle's finder syntax uses literal ';' ',' '=' which must not be percent-encoded.
        return f"{self.base}/hcmRestApi/resources/latest/{resource}?onlyData=true{extra}&finder={finder}"

    def job_url(self, job_id):
        return f"{self.base}/hcmUI/CandidateExperience/{self.lang}/sites/{self.site}/job/{job_id}"

    def list_jobs(self):
        """Yields every open requisition on the site (summary fields only)."""
        offset = 0
        total = None
        while total is None or offset < total:
            finder = f"findReqs;siteNumber={self.site},limit={PAGE_SIZE},offset={offset},sortBy=POSTING_DATES_DESC"
            data = _get_json(self._api("recruitingCEJobRequisitions", finder, "&expand=requisitionList.secondaryLocations"))
            items = data.get("items") or []
            if not items:
                break
            block = items[0]
            total = block.get("TotalJobsCount") or 0
            reqs = block.get("requisitionList") or []
            if not reqs:
                break
            yield from reqs
            offset += len(reqs)
            time.sleep(0.3)

    def in_selected_countries(self, req):
        if not self.countries:
            return True
        codes = {(req.get("PrimaryLocationCountry") or "").upper()}
        names = [req.get("PrimaryLocation") or ""]
        for loc in req.get("secondaryLocations") or []:
            codes.add((loc.get("CountryCode") or "").upper())
            names.append(loc.get("Name") or "")
        if codes & self.countries:
            return True
        text = " ".join(names).lower()
        return any(n in text for c in self.countries for n in COUNTRY_NAMES.get(c, []))

    def details(self, job_id):
        finder = f"ById;Id=%22{urllib.parse.quote(str(job_id))}%22,siteNumber={self.site}"
        data = _get_json(self._api("recruitingCEJobRequisitionDetails", finder, "&expand=all"))
        items = data.get("items") or []
        return items[0] if items else {}

    @staticmethod
    def locations(req):
        locs = [req.get("PrimaryLocation")]
        locs += [l.get("Name") for l in req.get("secondaryLocations") or []]
        seen, out = set(), []
        for l in locs:
            if l and l not in seen:
                seen.add(l)
                out.append(l)
        return out

    @staticmethod
    def categories(req):
        return [req.get("JobFamily"), req.get("JobFunction"), req.get("Category")]

    @staticmethod
    def description_from_details(d):
        sections = [
            ("", d.get("ExternalDescriptionStr")),
            ("Responsibilities", d.get("ExternalResponsibilitiesStr")),
            ("Qualifications", d.get("ExternalQualificationsStr")),
        ]
        parts = []
        for heading, raw in sections:
            text = html_to_text(raw)
            if text:
                parts.append(f"{heading}\n{text}" if heading else text)
        return "\n\n".join(parts)
