import unittest

from it_filter import ITFilter


class ITFilterTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.f = ITFilter.load()

    def test_it_titles(self):
        for title in [
            "Senior Software Engineer", "DevOps Engineer", "Cloud Security Architect", "IT Support Specialist",
            "Data Scientist", "Network Engineer - IP/MPLS", "Technical Support Engineer", "Systems Engineer (VLE) - Dubai",
            "Manager - AI Platforms", "QA Automation Engineer", "SAP ABAP Consultant", "SOC Analyst L2",
            "Software Development Engineer (Machine Learning)", "Head of Digital Transformation",
        ]:
            self.assertTrue(self.f.is_it_job(title), title)

    def test_non_it_titles(self):
        for title in [
            "Account Manager", "Senior Accountant", "Retail Store Manager", "Talent Acquisition Partner",
            "Legal Counsel", "Digital Marketing Specialist", "Driver", "Inside Sales Representative",
            "Make it happen: Customer Experience Lead", "Sr. Analyst/Corporate HSE & Security (UAE National)",
        ]:
            self.assertFalse(self.f.is_it_job(title), title)

    def test_category_match(self):
        self.assertTrue(self.f.is_it_job("Specialist", ["Information Technology"]))
        self.assertFalse(self.f.is_it_job("Specialist", ["Finance"]))


if __name__ == "__main__":
    unittest.main()
