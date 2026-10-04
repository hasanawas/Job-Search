import unittest
from unittest import mock

import oracle_hcm
import phenom
import scrape
import smartrecruiters
import workday
from common import country_code, html_to_text
from it_filter import FieldTagger, ITFilter

DEFAULTS = {"countries": ["AE", "LK"]}


def run(cfg, module, responder, previous=()):
    with mock.patch.object(module, "fetch_json", side_effect=responder), mock.patch.object(module.time, "sleep"):
        return scrape.scrape_source(cfg, DEFAULTS, ITFilter.load(), FieldTagger.load(), list(previous), "NOW", lambda m: None)


class OracleTest(unittest.TestCase):
    LIST = {"items": [{"TotalJobsCount": 3, "requisitionList": [
        {"Id": "101", "Title": "Cloud Engineer", "PostedDate": "2026-10-01", "PrimaryLocation": "Dubai, United Arab Emirates",
         "PrimaryLocationCountry": "AE", "ShortDescriptionStr": "Run our cloud", "secondaryLocations": []},
        {"Id": "102", "Title": "Software Engineer", "PrimaryLocation": "Sunnyvale, CA, United States", "PrimaryLocationCountry": "US",
         "secondaryLocations": [{"Name": "Abu Dhabi, United Arab Emirates", "CountryCode": "AE"}]},
        {"Id": "103", "Title": "Software Engineer", "PrimaryLocation": "Tokyo, Japan", "PrimaryLocationCountry": "JP"},
    ]}]}
    DETAILS = {"items": [{"ExternalDescriptionStr": "<p>Hello&nbsp;team</p><ul><li>AWS</li><li>K8s</li></ul>"}]}

    def test_filters_tags_and_keeps_first_seen(self):
        cfg = {"id": "x", "company": "X", "type": "oracle_hcm", "base_url": "https://h.example.com/", "site_number": "CX_9"}
        jobs, stats = run(cfg, oracle_hcm, lambda url, **kw: self.DETAILS if "Details" in url else self.LIST,
                          [{"id": "x:101", "first_seen": "OLD", "description": "kept"}])
        self.assertEqual(stats, {"listed": 3, "in_location": 2, "it": 2, "new": 1})
        by_id = {j["id"]: j for j in jobs}
        self.assertEqual(by_id["x:101"]["first_seen"], "OLD")
        self.assertEqual(by_id["x:101"]["description"], "kept")
        self.assertEqual(by_id["x:101"]["field"], "DevOps & Cloud")
        self.assertEqual(by_id["x:102"]["description"], "Hello team\n\n• AWS\n• K8s")
        self.assertEqual(by_id["x:102"]["country"], "United Arab Emirates")  # only the selected country is shown
        self.assertEqual(by_id["x:102"]["field"], "Software Development")
        self.assertEqual(by_id["x:102"]["url"], "https://h.example.com/hcmUI/CandidateExperience/en/sites/CX_9/job/102")


class SmartRecruitersTest(unittest.TestCase):
    def responder(self, url, **kw):
        if url.endswith("/postings/1"):
            return {"jobAd": {"sections": {"jobDescription": {"title": "Job Description", "text": "<p>Build things</p>"}}},
                    "postingUrl": "https://jobs.smartrecruiters.com/ifs1/1-dev"}
        return {"totalFound": 2, "content": [
            {"id": "1", "name": "IFS Cloud Developer", "releasedDate": "2026-10-02T17:48:22.034Z",
             "location": {"city": "Colombo", "country": "lk", "fullLocation": "Colombo, Sri Lanka", "hybrid": True},
             "function": {"label": "Information Technology"}},
            {"id": "2", "name": "Developer", "location": {"country": "in", "fullLocation": "Pune, India"}},
        ]}

    def test_postings(self):
        cfg = {"id": "ifs", "company": "IFS", "type": "smartrecruiters", "company_identifier": "ifs1"}
        jobs, stats = run(cfg, smartrecruiters, self.responder)
        self.assertEqual(stats["listed"], 2)
        self.assertEqual(len(jobs), 1)
        j = jobs[0]
        self.assertEqual((j["country"], j["workplace_type"], j["posted_date"]), ("Sri Lanka", "Hybrid", "2026-10-02"))
        self.assertEqual(j["url"], "https://jobs.smartrecruiters.com/ifs1/1-dev")
        self.assertEqual(j["description"], "Job Description\nBuild things")


class WorkdayTest(unittest.TestCase):
    FACETS = {"total": 3, "jobPostings": [], "facets": [{"facetParameter": "locationMainGroup", "values": [
        {"facetParameter": "locationCountry", "values": [
            {"descriptor": "United Arab Emirates", "id": "uae-id", "count": 1},
            {"descriptor": "India", "id": "in-id", "count": 2}]}]}]}

    def responder(self, url, data=None, **kw):
        if data is None:  # detail page
            return {"jobPostingInfo": {"jobDescription": "<p>Do DevOps</p>", "startDate": "2026-09-30",
                                       "location": "Dubai", "additionalLocations": ["Abu Dhabi"]}}
        if not data["appliedFacets"]:
            return self.FACETS
        self.assertEqual(data["appliedFacets"], {"locationCountry": ["uae-id"]})
        return {"total": 1, "jobPostings": [{"title": "DevOps Engineer", "externalPath": "/job/Dubai/DevOps-Engineer_R001",
                                             "locationsText": "Dubai", "postedOn": "Posted Yesterday"}]}

    def test_country_facets_and_details(self):
        cfg = {"id": "acc", "company": "Accenture", "type": "workday", "host": "acc.wd103.myworkdayjobs.com",
               "tenant": "acc", "site": "Careers"}
        jobs, _ = run(cfg, workday, self.responder)
        self.assertEqual(len(jobs), 1)
        j = jobs[0]
        self.assertEqual(j["id"], "acc:R001")
        self.assertEqual(j["url"], "https://acc.wd103.myworkdayjobs.com/en-US/Careers/job/Dubai/DevOps-Engineer_R001")
        self.assertEqual((j["country"], j["posted_date"], j["locations"]), ("United Arab Emirates", "2026-09-30", ["Dubai", "Abu Dhabi"]))
        self.assertEqual(j["description"], "Do DevOps")

    def test_fixed_facets(self):
        src = workday.WorkdaySource({"host": "wd5.myworkdaysite.com", "tenant": "sysco", "site": "syscocareers",
                                     "facets": {"locations": ["lk"]}, "country": "LK"})
        self.assertEqual(list(src._queries()), [("LK", {"locations": ["lk"]})])
        self.assertEqual(src.public, "https://wd5.myworkdaysite.com/en-US/recruiting/sysco/syscocareers")


class PhenomTest(unittest.TestCase):
    def responder(self, url, data=None, **kw):
        if data["ddoKey"] == "jobDetail":
            return {"jobDetail": {"data": {"job": {"description": "<p>Lead frontend</p>"}}}}
        return {"refineSearch": {"totalHits": 1, "data": {"jobs": [
            {"jobId": "3390", "title": "Senior Engineer - Frontend", "brand": "Inception42", "category": "Information Technology Operations",
             "multi_location": ["Abu Dhabi, Abu Dhabi, United Arab Emirates"], "postedDate": "2026-09-22T13:34:46.000+0000",
             "ml_job_parser": {"descriptionTeaser": "Teaser"}}]}}}

    def test_jobs(self):
        cfg = {"id": "g42", "company": "G42", "type": "phenom", "base_url": "https://careers.g42.ai", "brand_as_company": True,
               "countries": "all"}
        jobs, _ = run(cfg, phenom, self.responder)
        j = jobs[0]
        self.assertEqual(j["company"], "G42 · Inception42")
        self.assertEqual(j["url"], "https://careers.g42.ai/global/en/job/3390")
        self.assertEqual((j["country"], j["posted_date"], j["field"]), ("United Arab Emirates", "2026-09-22", "Software Development"))
        self.assertEqual(j["description"], "Lead frontend")


class CommonTest(unittest.TestCase):
    def test_country_code(self):
        self.assertEqual(country_code("Dubai, Dubai, United Arab Emirates"), "AE")
        self.assertEqual(country_code("Colombo 03"), "LK")
        self.assertEqual(country_code("Indianapolis, Indiana"), "")

    def test_html_to_text(self):
        self.assertEqual(html_to_text("<ul><li>a</li><li>b</li></ul>"), "• a\n• b")


if __name__ == "__main__":
    unittest.main()


class FailedSourceTest(unittest.TestCase):
    JOBS = [{"key": "a"}, {"key": "b"}]

    def test_keeps_recent_jobs_after_failure(self):
        kept, last_ok = scrape.keep_after_failure({"ok": True, "checked_at": "2026-10-04T02:00:00Z"}, self.JOBS, "2026-10-04T14:00:00Z")
        self.assertEqual((kept, last_ok), (self.JOBS, "2026-10-04T02:00:00Z"))

    def test_drops_jobs_not_confirmed_for_two_days(self):
        prev = {"ok": False, "last_ok_at": "2026-10-01T14:00:00Z"}
        kept, last_ok = scrape.keep_after_failure(prev, self.JOBS, "2026-10-04T14:00:00Z")
        self.assertEqual((kept, last_ok), ([], "2026-10-01T14:00:00Z"))

    def test_drops_jobs_with_no_good_check(self):
        self.assertEqual(scrape.keep_after_failure(None, self.JOBS, "2026-10-04T14:00:00Z"), ([], None))
