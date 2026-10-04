import unittest
from unittest import mock

import oracle_hcm
import scrape
from it_filter import ITFilter

LIST_PAGE = {"items": [{"TotalJobsCount": 3, "requisitionList": [
    {"Id": "101", "Title": "Cloud Engineer", "PostedDate": "2026-10-01", "PrimaryLocation": "Dubai, United Arab Emirates",
     "PrimaryLocationCountry": "AE", "ShortDescriptionStr": "Run our cloud", "secondaryLocations": []},
    {"Id": "102", "Title": "Software Engineer", "PostedDate": "2026-10-01", "PrimaryLocation": "Sunnyvale, CA, United States",
     "PrimaryLocationCountry": "US", "secondaryLocations": [{"Name": "Abu Dhabi, United Arab Emirates", "CountryCode": "AE"}]},
    {"Id": "103", "Title": "Account Manager", "PostedDate": "2026-10-01", "PrimaryLocation": "Dubai, United Arab Emirates",
     "PrimaryLocationCountry": "AE", "secondaryLocations": []},
]}]}
DETAILS = {"items": [{"ExternalDescriptionStr": "<p>Hello&nbsp;team</p><ul><li>AWS</li><li>K8s</li></ul>"}]}


def fake_get(url, retries=3):
    return DETAILS if "Details" in url else LIST_PAGE


class OracleHCMTest(unittest.TestCase):
    def test_scrape_source_filters_and_builds_jobs(self):
        cfg = {"id": "x", "company": "X", "type": "oracle_hcm", "base_url": "https://h.example.com/",
               "site_number": "CX_9", "countries": ["AE"]}
        with mock.patch.object(oracle_hcm, "_get_json", side_effect=fake_get), mock.patch.object(oracle_hcm.time, "sleep"):
            jobs, stats = scrape.scrape_source(cfg, ITFilter.load(), [{"id": "x:101", "first_seen": "OLD", "description": "kept"}],
                                               "NOW", print)
        self.assertEqual(stats, {"listed": 3, "in_location": 3, "it": 2, "new": 1})
        by_id = {j["id"]: j for j in jobs}
        self.assertEqual(by_id["x:101"]["first_seen"], "OLD")
        self.assertEqual(by_id["x:101"]["description"], "kept")
        self.assertEqual(by_id["x:102"]["first_seen"], "NOW")
        self.assertEqual(by_id["x:102"]["description"], "Hello team\n\n• AWS\n• K8s")
        self.assertEqual(by_id["x:102"]["url"], "https://h.example.com/hcmUI/CandidateExperience/en/sites/CX_9/job/102")

    def test_country_filter(self):
        s = oracle_hcm.OracleHCMSource({"base_url": "https://h", "site_number": "S", "countries": ["AE"]})
        self.assertFalse(s.in_selected_countries({"PrimaryLocation": "Tokyo, Japan", "PrimaryLocationCountry": "JP"}))
        self.assertTrue(s.in_selected_countries({"PrimaryLocation": "Dubai Internet City"}))


if __name__ == "__main__":
    unittest.main()
