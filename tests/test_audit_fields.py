import unittest

from jiramigrate.api import Api
from jiramigrate.audit import fields
from tests.helpers import FakeSession, load


def make_server():
    session = FakeSession().add("GET", r"/rest/api/2/field$", load("server_fields.json"))
    return Api("https://jira.corp.example.com", session=session), session


class FieldAuditTests(unittest.TestCase):
    def test_only_custom_fields(self):
        server, _ = make_server()
        got = fields.custom_fields(server)
        self.assertEqual(len(got), 8)
        self.assertTrue(all(f["custom"] for f in got))

    def test_field_types(self):
        server, _ = make_server()
        by_id = {f["id"]: fields.field_type(f) for f in fields.custom_fields(server)}
        self.assertEqual(by_id["customfield_10103"], "select")
        self.assertEqual(by_id["customfield_10102"], "gh-epic-link")
        self.assertEqual(by_id["customfield_10100"], "float")

    def test_duplicates_ignore_case(self):
        server, _ = make_server()
        rows = fields.duplicate_rows(fields.custom_fields(server))
        self.assertEqual(rows, [{"name": "Story Points", "type": "float", "ids": ["customfield_10100", "customfield_10101"],
                                 "variants": ["Story Points", "Story points"]}])


if __name__ == "__main__":
    unittest.main()
