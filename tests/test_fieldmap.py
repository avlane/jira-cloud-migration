import unittest

from jiramigrate import fieldmap
from jiramigrate.api import Api
from jiramigrate.audit import fields as audit_fields
from tests.helpers import FakeSession, load


def server_fields():
    return audit_fields.custom_fields(Api("https://jira.corp.example.com", session=FakeSession().add("GET", r"/field$", load("server_fields.json"))))


def cloud_fields():
    session = FakeSession().add("GET", r"/rest/api/3/field$", load("cloud_fields.json"))
    return fieldmap.cloud_custom_fields(Api("https://example.atlassian.net", prefix="/rest/api/3/", session=session))


class FieldMapTests(unittest.TestCase):
    def rows(self):
        return {r["serverId"]: r for r in fieldmap.map_fields(server_fields(), cloud_fields())}

    def test_cloud_custom_fields_only(self):
        self.assertEqual(len(cloud_fields()), 6)

    def test_matches_by_name_and_type(self):
        rows = self.rows()
        self.assertEqual((rows["customfield_10100"]["status"], rows["customfield_10100"]["cloudId"]), ("matched", "customfield_10200"))
        self.assertEqual(rows["customfield_10102"]["cloudId"], "customfield_10201")
        self.assertEqual(rows["customfield_10107"]["cloudId"], "customfield_10207")

    def test_case_differences_still_match(self):
        self.assertEqual(self.rows()["customfield_10101"]["cloudId"], "customfield_10200")

    def test_same_name_other_type_is_a_mismatch(self):
        row = self.rows()["customfield_10106"]
        self.assertEqual((row["status"], row["cloudId"]), ("type-mismatch", "customfield_10206"))
        self.assertEqual(row["note"], "Cloud field is a datetime")

    def test_missing(self):
        row = self.rows()["customfield_10105"]
        self.assertEqual((row["status"], row["cloudId"]), ("missing", ""))


if __name__ == "__main__":
    unittest.main()
