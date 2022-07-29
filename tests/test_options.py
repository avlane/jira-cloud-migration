import unittest

from jiramigrate import options
from jiramigrate.api import Api
from tests.helpers import FakeSession, load


class ServerOptionTests(unittest.TestCase):
    def setUp(self):
        self.session = FakeSession().add("GET", r"/rest/api/2/issue/createmeta$", load("server_createmeta.json"))
        self.found = options.server_options(Api("https://jira.corp.example.com", session=self.session))

    def test_requests_field_metadata(self):
        self.assertEqual(self.session.calls[0]["params"], {"expand": "projects.issuetypes.fields"})

    def test_only_custom_fields_with_allowed_values(self):
        self.assertEqual(sorted(self.found), ["customfield_10103", "customfield_10104", "customfield_10108"])

    def test_values_are_unioned_across_projects_and_issue_types(self):
        self.assertEqual(self.found["customfield_10103"]["values"], ["Blocker", "High", "Low", "Medium", "None"])
        self.assertEqual(self.found["customfield_10104"]["values"], ["dev", "dr-site", "prod", "staging"])

    def test_cascading_children(self):
        self.assertEqual(self.found["customfield_10108"]["values"], ["Laptop", "Laptop / Apple", "Laptop / Dell"])


if __name__ == "__main__":
    unittest.main()
