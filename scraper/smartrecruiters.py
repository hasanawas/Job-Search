"""Careers sites on SmartRecruiters (careers.smartrecruiters.com/<company>), e.g. IFS.
Uses SmartRecruiters' public postings API."""

import time

from common import country_name, fetch_json, html_to_text

API = "https://api.smartrecruiters.com/v1/companies"
PAGE_SIZE = 100


class SmartRecruitersSource:
    def __init__(self, cfg):
        self.company = cfg["company_identifier"]

    def fetch(self):
        offset, total = 0, None
        while total is None or offset < total:
            data = fetch_json(f"{API}/{self.company}/postings?limit={PAGE_SIZE}&offset={offset}")
            total = data.get("totalFound") or 0
            items = data.get("content") or []
            if not items:
                break
            for p in items:
                yield self._posting(p)
            offset += len(items)
            time.sleep(0.3)

    def _posting(self, p):
        loc = p.get("location") or {}
        code = (loc.get("country") or "").upper()
        full = loc.get("fullLocation") or ", ".join(x for x in [loc.get("city"), country_name(code)] if x)
        workplace = "Remote" if loc.get("remote") else "Hybrid" if loc.get("hybrid") else ""
        return {
            "key": str(p["id"]),
            "title": (p.get("name") or "").strip(),
            "locations": [full] if full else [],
            "countries": [code] if code else [],
            "workplace_type": workplace,
            "categories": [(p.get("function") or {}).get("label"), (p.get("department") or {}).get("label")],
            "posted_date": p.get("releasedDate") or "",
            "summary": "",
            "url": f"https://jobs.smartrecruiters.com/{self.company}/{p['id']}",
        }

    def details(self, posting):
        d = fetch_json(f"{API}/{self.company}/postings/{posting['key']}")
        sections = (d.get("jobAd") or {}).get("sections") or {}
        parts = []
        for name in ["jobDescription", "qualifications", "additionalInformation"]:
            s = sections.get(name) or {}
            text = html_to_text(s.get("text"))
            if text:
                parts.append(f"{s.get('title') or ''}\n{text}".strip())
        out = {"description": "\n\n".join(parts)}
        if d.get("postingUrl"):
            out["url"] = d["postingUrl"]
        return out
