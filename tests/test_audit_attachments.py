import unittest

from jiramigrate.api import Api
from jiramigrate.audit import attachments
from tests.helpers import FakeSession, load, search_handler


def make_server():
    session = FakeSession().add("GET", r"/rest/api/2/search$", search_handler(load("server_attachment_issues.json")))
    return Api("https://jira.corp.example.com", session=session), session


class AttachmentAuditTests(unittest.TestCase):
    def test_query_and_fields(self):
        server, session = make_server()
        list(attachments.iter_attachments(server))
        params = session.calls[0]["params"]
        self.assertEqual(params["jql"], "attachments is not EMPTY")
        self.assertEqual(params["fields"], "attachment,project")

    def test_oversized_default_limit(self):
        server, _ = make_server()
        rows = attachments.oversized(server)
        self.assertEqual([(r["issue"], r["filename"], r["sizeMB"]) for r in rows],
                         [("OPS-9", "huge-export.csv", 70.0), ("PLAT-12", "release-build.zip", 25.0), ("PLAT-31", "demo.mp4", 12.0)])

    def test_exactly_at_the_limit_is_allowed(self):
        server, _ = make_server()
        names = [r["filename"] for r in attachments.oversized(server, 10)]
        self.assertNotIn("db-dump.sql.gz", names)
        names = [r["filename"] for r in attachments.oversized(server, 9.9)]
        self.assertIn("db-dump.sql.gz", names)

    def test_totals_by_project(self):
        server, _ = make_server()
        rows = attachments.totals_by_project(server)
        self.assertEqual([(r["project"], r["files"], r["sizeMB"]) for r in rows], [("OPS", 3, 80.4), ("PLAT", 3, 37.0)])


if __name__ == "__main__":
    unittest.main()
