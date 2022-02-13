import io
import json
import unittest

from jiramigrate import cli
from jiramigrate.api import Api
from tests.helpers import FakeSession, counts_handler, load, paged


def run(argv, session):
    out = io.StringIO()
    code = cli.main(argv, server=Api("https://jira.corp.example.com", session=session), out=out)
    return code, out.getvalue()


class AuditCliTests(unittest.TestCase):
    def test_audit_fields_lists_duplicates(self):
        session = FakeSession().add("GET", r"/rest/api/2/field$", load("server_fields.json"))
        code, text = run(["audit", "fields", "--format", "json"], session)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(text)[0]["ids"], ["customfield_10100", "customfield_10101"])

    def test_audit_fields_unused(self):
        session = FakeSession().add("GET", r"/rest/api/2/field$", load("server_fields.json"))
        session.add("GET", r"/rest/api/2/search$", counts_handler({"cf[10105]": 0}, default=5))
        code, text = run(["audit", "fields", "--unused", "--format", "csv"], session)
        self.assertEqual(text.splitlines(), ["id,name,type,issues", "customfield_10105,Legacy Ref,textfield,0"])

    def test_audit_users_only_shows_problems(self):
        session = FakeSession().add("GET", r"/rest/api/2/user/search$", paged(load("server_users.json")))
        code, text = run(["audit", "users", "--format", "csv"], session)
        names = [line.split(",")[1] for line in text.splitlines()[1:]]
        self.assertEqual(names, ["dwhitfield", "svc-build", "econtractor", "ecastellano", "frank", "tmp-user"])

    def test_audit_attachments(self):
        from tests.helpers import search_handler
        session = FakeSession().add("GET", r"/rest/api/2/search$", search_handler(load("server_attachment_issues.json")))
        code, text = run(["audit", "attachments", "--limit-mb", "20", "--format", "csv"], session)
        self.assertEqual([line.split(",")[1] for line in text.splitlines()[1:]], ["OPS-9", "PLAT-12"])
        code, text = run(["audit", "attachments", "--totals", "--format", "csv"], session)
        self.assertEqual(text.splitlines()[1], "OPS,3,80.4")

    def test_audit_addons(self):
        session = FakeSession().add("GET", r"/rest/plugins/1.0/$", load("server_plugins.json"))
        code, text = run(["audit", "addons", "--format", "csv"], session)
        self.assertEqual(len(text.splitlines()), 5)
        self.assertIn("Timesheet for Jira", text)

    def test_errors_exit_with_2(self):
        from tests.helpers import FakeResponse
        session = FakeSession().add("GET", r"/field$", FakeResponse(401, {"message": "Unauthorized"}))
        code, text = run(["audit", "fields"], session)
        self.assertEqual(code, 2)
        self.assertEqual(text, "")


if __name__ == "__main__":
    unittest.main()
