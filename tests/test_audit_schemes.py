import unittest

from jiramigrate.api import Api
from jiramigrate.audit import schemes
from tests.helpers import FakeSession, load


def make_server():
    session = FakeSession()
    session.add("GET", r"/rest/api/2/project$", load("server_projects.json"))
    session.add("GET", r"/rest/api/2/permissionscheme$", load("server_permissionschemes.json"))
    session.add("GET", r"/rest/api/2/notificationscheme$", load("server_notificationschemes.json"))
    for key in ("plat", "ops", "legacy"):
        session.add("GET", r"/project/%s/permissionscheme$" % key.upper(), load("server_%s_permissionscheme.json" % key))
        session.add("GET", r"/project/%s/notificationscheme$" % key.upper(), load("server_%s_notificationscheme.json" % key))
    return Api("https://jira.corp.example.com", session=session), session


class SchemeAuditTests(unittest.TestCase):
    def test_unused_schemes(self):
        server, _ = make_server()
        rows = schemes.report(server)
        unused = [(r["kind"], r["name"]) for r in rows if r["finding"]]
        self.assertEqual(unused, [("permission", "2018 Contractor Access"), ("notification", "Everything To Everyone")])

    def test_used_schemes_list_their_projects(self):
        server, _ = make_server()
        by_name = {(r["kind"], r["name"]): r["projects"] for r in schemes.report(server)}
        self.assertEqual(by_name[("permission", "Default Permission Scheme")], ["PLAT", "LEGACY"])
        self.assertEqual(by_name[("notification", "OPS Notifications")], ["OPS"])


    def test_unreadable_projects_make_findings_uncertain(self):
        from tests.helpers import FakeResponse
        server, session = make_server()
        session.routes.insert(0, ("GET", __import__("re").compile(r"/project/OPS/permissionscheme$"), FakeResponse(403, {"errorMessages": ["no"]})))
        rows = schemes.report(server)
        by_name = {(r["kind"], r["name"]): r["finding"] for r in rows}
        self.assertEqual(by_name[("project", "OPS")], "project-unreadable")
        self.assertEqual(by_name[("permission", "2018 Contractor Access")], "maybe-unused")
        self.assertEqual(by_name[("permission", "Open Intake")], "maybe-unused")


if __name__ == "__main__":
    unittest.main()
