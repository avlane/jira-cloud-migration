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


class UsageTests(unittest.TestCase):
    def test_counts_and_unsearchable_fields(self):
        from tests.helpers import FakeResponse, counts_handler

        def search(call):
            jql = call["params"]["jql"]
            if "10102" in jql:
                return FakeResponse(400, {"errorMessages": ["Field 'cf[10102]' does not support searching"]})
            return counts_handler({"cf[10100]": 240, "cf[10105]": 0})(call)

        server, session = make_server()
        session.add("GET", r"/rest/api/2/search$", search)
        rows = fields.usage(server, fields.custom_fields(server))
        by_id = {r["id"]: r["issues"] for r in rows}
        self.assertEqual(by_id["customfield_10100"], 240)
        self.assertEqual(by_id["customfield_10105"], 0)
        self.assertIsNone(by_id["customfield_10102"])
        self.assertEqual(by_id["customfield_10101"], 0)
        self.assertEqual([r["id"] for r in fields.unused(rows)], ["customfield_10101", "customfield_10103", "customfield_10104", "customfield_10105", "customfield_10106", "customfield_10107"])

    def test_other_errors_propagate(self):
        from jiramigrate.api import ApiError
        from tests.helpers import FakeResponse
        server, session = make_server()
        session.add("GET", r"/rest/api/2/search$", FakeResponse(500, "boom"))
        with self.assertRaises(ApiError):
            fields.usage(server, fields.custom_fields(server)[:1])


if __name__ == "__main__":
    unittest.main()
