import unittest
from unittest import mock

import jsearch
import scrape
from it_filter import ITFilter

RESULTS = {"data": [
    {"job_id": "a1", "job_title": "DevOps Engineer", "employer_name": "Careem", "job_publisher": "LinkedIn",
     "job_city": "Dubai", "job_country": "AE", "job_posted_at_datetime_utc": "2026-10-03T08:00:00.000Z",
     "job_apply_link": "https://www.linkedin.com/jobs/view/1", "job_description": "Build pipelines",
     "apply_options": [{"publisher": "LinkedIn", "apply_link": "https://www.linkedin.com/jobs/view/1", "is_direct": False},
                       {"publisher": "Careem", "apply_link": "https://careers.careem.com/1", "is_direct": True}]},
    {"job_id": "a2", "job_title": "Sales Manager", "employer_name": "Acme", "job_publisher": "Bayt"},
    {"job_id": "a3", "job_title": "Systems Engineer - SASE", "employer_name": "Fortinet Inc.", "job_publisher": "LinkedIn",
     "job_apply_link": "https://x"},
]}


class JSearchTest(unittest.TestCase):
    def run_scrape(self, previous):
        cfg = {"id": "jb", "company": "Boards", "type": "jsearch", "queries": ["q1", "q2"]}
        known = {(scrape.norm("Fortinet"), scrape.norm("Systems Engineer - SASE"))}
        with mock.patch.dict("os.environ", {"JSEARCH_API_KEY": "k"}), \
                mock.patch.object(jsearch, "_get_json", return_value=RESULTS) as get, \
                mock.patch.object(jsearch.time, "sleep"):
            jobs, stats = scrape.scrape_source(cfg, ITFilter.load(), previous, "2026-10-04T00:00:00Z", lambda m: None, known)
        return jobs, stats, get

    def test_filters_dedupes_and_prefers_direct_link(self):
        jobs, stats, get = self.run_scrape([])
        self.assertEqual(get.call_count, 2)
        self.assertEqual([j["title"] for j in jobs], ["DevOps Engineer"])  # sales dropped, Fortinet already known
        job = jobs[0]
        self.assertEqual(job["url"], "https://careers.careem.com/1")
        self.assertEqual(job["via"], "LinkedIn")
        self.assertEqual(job["locations"], ["Dubai, United Arab Emirates"])
        self.assertEqual(job["posted_date"], "2026-10-03")
        self.assertEqual(stats["new"], 1)

    def test_keeps_recent_unlisted_jobs_and_drops_old_ones(self):
        recent = {"id": "jb:old1", "title": "Recent", "first_seen": scrape.now_iso()}
        stale = {"id": "jb:old2", "title": "Stale", "first_seen": "2020-01-01T00:00:00Z"}
        jobs, _, _ = self.run_scrape([recent, stale])
        titles = [j["title"] for j in jobs]
        self.assertIn("Recent", titles)
        self.assertNotIn("Stale", titles)

    def test_disabled_without_key(self):
        with mock.patch.dict("os.environ", {"JSEARCH_API_KEY": ""}):
            self.assertFalse(jsearch.JSearchSource({"queries": []}).enabled)


if __name__ == "__main__":
    unittest.main()
