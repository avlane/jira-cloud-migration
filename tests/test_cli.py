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


class MapCliTests(unittest.TestCase):
    def run_map(self, argv, server_session, cloud_session):
        out = io.StringIO()
        code = cli.main(argv, server=Api("https://jira.corp.example.com", session=server_session), out=out,
                        cloud=Api("https://example.atlassian.net", prefix="/rest/api/3/", session=cloud_session))
        return code, out.getvalue()

    def test_map_users_writes_a_mapping_file(self):
        import os
        import tempfile
        results = load("cloud_user_search.json")
        server = FakeSession().add("GET", r"/rest/api/2/user/search$", paged(load("server_users.json")))
        cloud = FakeSession().add("GET", r"/user/search$", lambda call: results.get(call["params"]["query"].lower(), []))
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "users.json")
            code, text = self.run_map(["map", "users", "-o", path, "--format", "csv"], server, cloud)
            with open(path, encoding="utf-8") as handle:
                data = json.load(handle)
        self.assertEqual(code, 0)
        self.assertEqual(data["kind"], "users")
        self.assertEqual(data["summary"], {"matched": 4, "probable": 1, "no-email": 2, "duplicate": 1, "missing": 1})
        self.assertEqual(data["server"], "https://jira.corp.example.com")
        self.assertEqual(text.splitlines()[0], "serverKey,serverName,displayName,email,accountId,cloudName,status,note")

    def test_map_fields_and_names(self):
        server = FakeSession().add("GET", r"/rest/api/2/field$", load("server_fields.json"))
        cloud = FakeSession().add("GET", r"/rest/api/3/field$", load("cloud_fields.json"))
        code, text = self.run_map(["map", "fields", "--format", "json"], server, cloud)
        self.assertEqual({r["serverId"]: r["status"] for r in json.loads(text)}["customfield_10106"], "type-mismatch")
        from tests.test_namemap import sites
        server_api, cloud_api = sites()
        out = io.StringIO()
        code = cli.main(["map", "names", "--format", "csv"], server=server_api, cloud=cloud_api, out=out)
        self.assertEqual(code, 0)
        self.assertIn("status,Open,10000,,,missing", out.getvalue())


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

    def test_audit_addons_with_a_cloud_apps_file(self):
        import os
        import tempfile
        session = FakeSession().add("GET", r"/rest/plugins/1.0/$", load("server_plugins.json"))
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "apps.json")
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(load("cloud_apps.json"), handle)
            code, text = run(["audit", "addons", "--cloud-apps", path, "--format", "json"], session)
        findings = {r["key"]: r["finding"] for r in json.loads(text)}
        self.assertEqual(findings["com.example.theme"], "no-cloud-version")

    def test_snapshot_command(self):
        import os
        import tempfile
        from tests.test_snapshot import search
        session = FakeSession().add("GET", r"/rest/api/2/project$", load("server_projects.json")).add("GET", r"/rest/api/2/search$", search)
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "snap.json")
            code, text = run(["snapshot", "-o", path], session)
            with open(path, encoding="utf-8") as handle:
                saved = json.load(handle)
        self.assertEqual(code, 0)
        self.assertIn("saved 3 projects (2045 issues)", text)
        self.assertEqual(saved["projects"]["OPS"]["issues"], 845)

    def test_errors_exit_with_2(self):
        from tests.helpers import FakeResponse
        session = FakeSession().add("GET", r"/field$", FakeResponse(401, {"message": "Unauthorized"}))
        code, text = run(["audit", "fields"], session)
        self.assertEqual(code, 2)
        self.assertEqual(text, "")


if __name__ == "__main__":
    unittest.main()
