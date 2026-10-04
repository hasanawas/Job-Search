"""Jobs from LinkedIn, Indeed, Bayt, Glassdoor and other boards via the JSearch API
(https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch), which reads Google for Jobs.

LinkedIn has no public jobs API and forbids scraping, so this is the legitimate
way to include its listings. Needs a RapidAPI key in the JSEARCH_API_KEY
environment variable; the free plan allows 200 requests a month and each query
costs one request per run."""

import json
import os
import time
import urllib.parse
import urllib.request

from common import country_name

HOST = "jsearch.p.rapidapi.com"
KEY_ENV = "JSEARCH_API_KEY"


def _get_json(url, key, retries=3):
    last_error = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"X-RapidAPI-Key": key, "X-RapidAPI-Host": HOST,
                                                       "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as e:
            if e.code in (401, 403, 429):  # bad key or quota used up: retrying won't help
                raise RuntimeError(f"JSearch returned HTTP {e.code} (check the API key and monthly quota)")
            last_error = e
        except Exception as e:
            last_error = e
        time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"JSearch request failed: {last_error}")


class JSearchSource:
    keep_unlisted_days = 21  # search only covers recent posts, so keep jobs it found earlier this long
    needs_key = KEY_ENV

    def __init__(self, source):
        self.source = source
        self.key = os.environ.get(KEY_ENV, "").strip()
        self.queries = source.get("queries", [])
        self.country = source.get("search_country", "ae")
        self.date_posted = source.get("date_posted", "3days")
        self.publishers = {p.lower() for p in source.get("publishers", [])}

    @property
    def enabled(self):
        return bool(self.key)

    def search(self, query):
        params = urllib.parse.urlencode({"query": query, "page": 1, "num_pages": 1,
                                         "country": self.country, "date_posted": self.date_posted})
        data = _get_json(f"https://{HOST}/search?{params}", self.key)
        return data.get("data") or []

    def fetch(self):
        """Yields de-duplicated postings from every configured query."""
        seen = set()
        for query in self.queries:
            for job in self.search(query):
                jid = job.get("job_id")
                if not jid or jid in seen:
                    continue
                seen.add(jid)
                if self.publishers and (job.get("job_publisher") or "").lower() not in self.publishers:
                    continue
                yield self._posting(job)
            time.sleep(1)

    def _posting(self, job):
        code = (job.get("job_country") or "").upper()
        place = ", ".join(p for p in [job.get("job_city"), job.get("job_state")] if p)
        loc = ", ".join(p for p in [place, country_name(code)] if p)
        return {
            "key": job["job_id"],
            "title": (job.get("job_title") or "").strip(),
            "company": (job.get("employer_name") or "").strip() or "Unknown company",
            "via": job.get("job_publisher") or "",
            "locations": [loc] if loc else [],
            "countries": [code] if code else [],
            "workplace_type": "Remote" if job.get("job_is_remote") else "",
            "categories": [],
            "posted_date": (job.get("job_posted_at_datetime_utc") or "")[:10],
            "summary": "",
            "url": self.apply_url(job),
            "description": (job.get("job_description") or "").strip()[:8000],
        }

    @staticmethod
    def apply_url(job):
        """Prefers the employer's own site, then LinkedIn, then whatever board Google found."""
        options = job.get("apply_options") or []
        for opt in options:
            if opt.get("is_direct") and opt.get("apply_link"):
                return opt["apply_link"]
        for opt in options:
            if (opt.get("publisher") or "").lower() == "linkedin" and opt.get("apply_link"):
                return opt["apply_link"]
        return job.get("job_apply_link") or (options[0].get("apply_link") if options else "")
