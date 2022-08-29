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


def cloud_site():
    session = FakeSession()
    session.add("GET", r"/field/customfield_10203/context$", load("cloud_contexts_10203.json"))
    session.add("GET", r"/field/customfield_10203/context/10300/option$", load("cloud_options_10203_10300.json"))
    session.add("GET", r"/field/customfield_10204/context$", load("cloud_contexts_10204.json"))
    session.add("GET", r"/field/customfield_10204/context/10301/option$", load("cloud_options_10204_10301.json"))
    session.add("GET", r"/field/customfield_10204/context/10302/option$", load("cloud_options_10204_10302.json"))
    return Api("https://example.atlassian.net", prefix="/rest/api/3/", session=session), session


class CloudOptionTests(unittest.TestCase):
    def test_options_are_unioned_over_contexts(self):
        cloud, session = cloud_site()
        self.assertEqual(options.cloud_options(cloud, "customfield_10204"), ["dev", "prod", "staging"])
        self.assertEqual(len(session.calls_to("GET", "/option")), 2)

    def test_child_options_are_labelled_with_their_parent(self):
        session = FakeSession()
        session.add("GET", r"/context$", {"values": [{"id": "1"}], "isLast": True})
        session.add("GET", r"/context/1/option$", {"isLast": True, "values": [
            {"id": "5", "value": "Laptop", "disabled": False}, {"id": "6", "value": "Dell", "disabled": False, "optionId": "5"}]})
        cloud = Api("https://example.atlassian.net", prefix="/rest/api/3/", session=session)
        self.assertEqual(options.cloud_options(cloud, "customfield_1"), ["Laptop", "Laptop / Dell"])

    def test_compare(self):
        cloud, _ = cloud_site()
        server_opts = {"customfield_10103": {"name": "Customer Impact", "values": ["Blocker", "High", "Low", "Medium", "None"]},
                       "customfield_10104": {"name": "Affected Environments", "values": ["dev", "dr-site", "prod", "staging"]},
                       "customfield_10108": {"name": "Hardware", "values": ["Laptop"]}}
        field_rows = [{"serverId": "customfield_10103", "cloudId": "customfield_10203", "status": "matched"},
                      {"serverId": "customfield_10104", "cloudId": "customfield_10204", "status": "matched"},
                      {"serverId": "customfield_10108", "cloudId": "", "status": "missing"}]
        rows = {r["serverId"]: r for r in options.compare(cloud, server_opts, field_rows)}
        self.assertEqual(rows["customfield_10103"]["missingOnCloud"], ["Blocker", "None"])
        self.assertEqual(rows["customfield_10103"]["extraOnCloud"], ["Legacy"])
        self.assertEqual(rows["customfield_10103"]["status"], "differs")
        self.assertEqual(rows["customfield_10104"]["missingOnCloud"], ["dr-site"])
        self.assertEqual(rows["customfield_10108"]["status"], "no-cloud-field")

    def test_matching_is_case_insensitive(self):
        cloud, _ = cloud_site()
        rows = options.compare(cloud, {"customfield_10204": {"name": "x", "values": ["PROD", "Staging", "DEV"]}},
                               [{"serverId": "customfield_10204", "cloudId": "customfield_10204", "status": "matched"}])
        self.assertEqual((rows[0]["status"], rows[0]["missingOnCloud"]), ("complete", []))


if __name__ == "__main__":
    unittest.main()
