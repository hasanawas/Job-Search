import json
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


class TeamtailorTest(unittest.TestCase):
    RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:tt="https://teamtailor.com/locations"><channel>
<item><title>Senior QA Engineer</title><description>&lt;p&gt;Test our &lt;b&gt;APIs&lt;/b&gt;&lt;/p&gt;</description>
<pubDate>Fri, 18 Sep 2026 17:20:14 +0400</pubDate><link>https://careers.example.ae/jobs/8039073-senior-qa-engineer</link>
<remoteStatus>hybrid</remoteStatus><tt:locations><tt:location><tt:name>Dubai</tt:name><tt:city>Dubai</tt:city>
<tt:country>United Arab Emirates</tt:country></tt:location></tt:locations><tt:department>Engineering</tt:department></item>
<item><title>Head of Marketing</title><description/><pubDate>Fri, 18 Sep 2026 17:20:14 +0400</pubDate>
<link>https://careers.example.ae/jobs/1-head-of-marketing</link><tt:locations><tt:location><tt:city>Dubai</tt:city>
<tt:country>United Arab Emirates</tt:country></tt:location></tt:locations></item>
</channel></rss>"""

    def test_reads_rss(self):
        import teamtailor
        cfg = {"id": "tt", "company": "Example", "type": "teamtailor", "base_url": "https://careers.example.ae"}
        with mock.patch.object(teamtailor, "fetch_text", return_value=self.RSS):
            jobs, stats = scrape.scrape_source(cfg, DEFAULTS, ITFilter.load(), FieldTagger.load(), [], "NOW", lambda m: None)
        self.assertEqual(stats["listed"], 2)
        self.assertEqual([j["title"] for j in jobs], ["Senior QA Engineer"])
        j = jobs[0]
        self.assertEqual((j["country"], j["posted_date"], j["workplace_type"]), ("United Arab Emirates", "2026-09-18", "Hybrid"))
        self.assertEqual(j["url"], "https://careers.example.ae/jobs/8039073-senior-qa-engineer")
        self.assertEqual(j["description"], "Test our APIs")


class JibeTest(unittest.TestCase):
    def page(self, url, data=None, headers=None):
        jobs = {1: [{"data": {"slug": "6556", "title": "Data Engineer", "tags2": ["Abu Dhabi"], "tags3": ["United Arab Emirates"],
                              "categories": [{"name": "Information Technology"}], "posted_date": "2026-10-06T11:29:00+0000",
                              "description": "<p>Build pipelines</p>"}}],
                2: [{"data": {"slug": "7000", "title": "Staff Nurse", "tags3": ["United Arab Emirates"], "categories": [{"name": "Nursing"}]}}]}
        page = int(url.split("page=")[1].split("&")[0])
        return {"totalCount": 2, "jobs": jobs.get(page, [])}

    def test_pages_and_filters(self):
        import jibe
        cfg = {"id": "jb", "company": "Example", "type": "jibe", "base_url": "https://careers.example.ae"}
        jobs, stats = run(cfg, jibe, self.page)
        self.assertEqual(stats["listed"], 2)
        self.assertEqual([j["title"] for j in jobs], ["Data Engineer"])
        j = jobs[0]
        self.assertEqual((j["country"], j["posted_date"], j["url"]), ("United Arab Emirates", "2026-10-06", "https://careers.example.ae/jobs/6556"))
        self.assertIn("Build pipelines", j["description"])


class AmazonTest(unittest.TestCase):
    JOB = {"id": "u1", "id_icims": "10571684", "title": "Sr. Solutions Architect, CS MENAT", "job_path": "/en/jobs/10571684/sr-sa",
           "locations": ['{"countryIso2a":"AE","normalizedCityName":"Dubai","normalizedCountryName":"United Arab Emirates"}'],
           "job_category": "Solutions Architect", "posted_date": "October  7, 2026", "description": "<p>Design on AWS</p>",
           "basic_qualifications": "- 5 years", "description_short": "Design"}
    OTHER = {"id": "u2", "id_icims": "2", "title": "Logistics Supervisor", "job_path": "/en/jobs/2/x",
             "locations": ['{"countryIso2a":"AE","normalizedCountryName":"United Arab Emirates"}'], "job_category": "Administrative Support"}

    def responder(self, url, data=None, headers=None):
        if "=ARE" in url and "offset=0" in url:
            return {"hits": 2, "jobs": [self.JOB, self.OTHER]}
        return {"hits": 0, "jobs": []}

    def test_jobs(self):
        import amazon
        jobs, stats = run({"id": "amazon", "company": "Amazon", "type": "amazon"}, amazon, self.responder)
        self.assertEqual(stats["listed"], 2)
        self.assertEqual([j["title"] for j in jobs], ["Sr. Solutions Architect, CS MENAT"])
        j = jobs[0]
        self.assertEqual((j["country"], j["posted_date"], j["url"]),
                         ("United Arab Emirates", "2026-10-07", "https://www.amazon.jobs/en/jobs/10571684/sr-sa"))
        self.assertIn("Design on AWS", j["description"])
        self.assertIn("Basic qualifications", j["description"])


class AppleTest(unittest.TestCase):
    def page(self, results, total):
        data = {"loaderData": {"root": {}, "search": {"searchResults": results, "totalRecords": total}}}
        return "<script>window.__staticRouterHydrationData = JSON.parse(%s);</script>" % json.dumps(json.dumps(data))

    def test_jobs(self):
        import apple
        it = {"positionId": "200", "postingTitle": "Software Engineer, Maps", "transformedPostingTitle": "software-engineer-maps",
              "locations": [{"countryName": "United Arab Emirates", "countryID": "iso-country-ARE"}], "team": {"teamName": "Software and Services"},
              "postDateInGMT": "2026-10-08T07:31:20Z", "jobSummary": "Build maps"}
        retail = {"positionId": "100", "postingTitle": "UAE-Business Expert", "transformedPostingTitle": "uae-business-expert",
                  "locations": [{"countryName": "United Arab Emirates", "countryID": "iso-country-ARE"}], "team": {"teamName": "Apple Retail"}}
        calls = []

        def fetch(url, *a, **k):
            calls.append(url)
            if "united-arab-emirates-ARE" in url:
                return self.page([retail, it], 3) if "page=1" in url else self.page([retail], 3)
            return self.page([], 0)
        with mock.patch.object(apple, "fetch_text", side_effect=fetch), mock.patch.object(apple.time, "sleep"):
            jobs, stats = scrape.scrape_source({"id": "apple", "company": "Apple", "type": "apple"}, DEFAULTS,
                                               ITFilter.load(), FieldTagger.load(), [], "NOW", lambda m: None)
        self.assertEqual(stats["listed"], 2)  # the repeat on page 2 is skipped
        self.assertEqual([j["title"] for j in jobs], ["Software Engineer, Maps"])
        self.assertEqual(jobs[0]["url"], "https://jobs.apple.com/en-ae/details/200/software-engineer-maps")
        self.assertEqual(jobs[0]["posted_date"], "2026-10-08")
        self.assertTrue(any("sri-lanka-LKA" in c for c in calls))


class SuccessFactorsTest(unittest.TestCase):
    ROW = ('<tr class="data-row"> <td class="colTitle" headers="hdrTitle"> <span class="jobTitle hidden-phone"> '
           '<a href="/job/Abu-Dhabi-{slug}-Abu/{id}/" class="jobTitle-link">{title}</a> </span> </td> '
           '<td class="colFacility hidden-phone"> <span class="jobFacility">{fac}</span> </td> '
           '<td class="colDate hidden-phone"> <span class="jobDate">18 Sept 2026 </span> </td> </tr>')

    def page(self, rows, total):
        label = f'<span class="paginationLabel" aria-label="x">Results <b>1 – 2</b> of <b>{total}</b></span>'
        return label + "<table>" + "".join(self.ROW.format(**r) for r in rows) + "</table>"

    def test_pages_and_details(self):
        import successfactors
        p0 = [{"slug": "Cloud-Engineer", "id": "1", "title": "Cloud Engineer", "fac": "Katim"},
              {"slug": "Sr_-Buyer", "id": "2", "title": "Sr. Buyer", "fac": "NIMR"}]
        detail = ('<span class="jobdescription"><p>Run our cloud</p></span></div>'
                  '<meta itemprop="addressLocality" content="Abu Dhabi"><meta itemprop="addressCountry" content="AE">')

        def fetch(url, *a, **k):
            if "/job/" in url:
                return detail
            return self.page(p0, 2) if url.endswith("/4166222/") else self.page([], 2)
        cfg = {"id": "edge", "company": "EDGE", "type": "successfactors", "base_url": "https://careers.example.ae",
               "list_path": "/go/View-All-Jobs/4166222/", "country": "AE", "facility_as_company": True}
        with mock.patch.object(successfactors, "fetch_text", side_effect=fetch), mock.patch.object(successfactors.time, "sleep"):
            jobs, stats = scrape.scrape_source(cfg, DEFAULTS, ITFilter.load(), FieldTagger.load(), [], "NOW", lambda m: None)
        self.assertEqual(stats["listed"], 2)
        self.assertEqual([j["title"] for j in jobs], ["Cloud Engineer"])
        j = jobs[0]
        self.assertEqual((j["company"], j["country"], j["posted_date"]), ("EDGE · Katim", "United Arab Emirates", "2026-09-18"))
        self.assertEqual(j["url"], "https://careers.example.ae/job/Abu-Dhabi-Cloud-Engineer-Abu/1/")
        self.assertEqual(j["description"], "Run our cloud")


class MichaelPageTest(unittest.TestCase):
    TILE = ('<li class="views-row"><div class="job-tile search-job-tile"><div class="job-title "><h3>'
            '<a href="/job-detail/{slug}/ref/{ref}" rel="bookmark">{title}</a></h3></div><div class="job-properties">'
            '<div class="job-location"><i class="fal"></i> Dubai</div></div><div class="job-summary">'
            '<div class="job_advert__job-summary-text"><p>{summary}</p></div></div></div></li>')

    def test_tiles_and_details(self):
        import michaelpage
        listing = "<ul>" + self.TILE.format(slug="head-of-devops", ref="jn-1", title="Head of DevOps", summary="Lead platform") + \
                  self.TILE.format(slug="sales-director", ref="jn-2", title="Sales Director - Technology", summary="Sell") + "</ul>"
        detail = ('<script type="application/ld+json">{"@type" : "JobPosting","datePosted" : "2026-10-01",'
                  '"description" : "<p>Kubernetes at scale</p>"}</script>')

        def fetch(url, *a, **k):
            return detail if "/job-detail/" in url else listing
        cfg = {"id": "mp", "company": "Michael Page (recruiter)", "type": "michaelpage", "base_url": "https://www.example.ae",
               "list_path": "/jobs/technology/united-arab-emirates", "country": "AE"}
        with mock.patch.object(michaelpage, "fetch_text", side_effect=fetch), mock.patch.object(michaelpage.time, "sleep"):
            jobs, stats = scrape.scrape_source(cfg, DEFAULTS, ITFilter.load(), FieldTagger.load(), [], "NOW", lambda m: None)
        self.assertEqual(stats["listed"], 2)
        self.assertEqual([j["title"] for j in jobs], ["Head of DevOps"])
        j = jobs[0]
        self.assertEqual((j["country"], j["posted_date"], j["description"]), ("United Arab Emirates", "2026-10-01", "Kubernetes at scale"))
        self.assertEqual(j["url"], "https://www.example.ae/job-detail/head-of-devops/ref/jn-1")
