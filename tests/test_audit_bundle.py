import unittest

from jiramigrate.api import Api
from jiramigrate.audit import bundle
from tests.helpers import FakeSession, load, paged, search_handler


def make_server():
    session = FakeSession()
    session.add("GET", r"/rest/api/2/field$", load("server_fields.json"))
    session.add("GET", r"/rest/api/2/user/search$", paged(load("server_users.json")))
    session.add("GET", r"/rest/api/2/project$", load("server_projects.json"))
    session.add("GET", r"/rest/api/2/workflow$", load("server_workflows.json"))
    session.add("GET", r"/rest/api/2/search$", search_handler(load("server_attachment_issues.json")))
    session.add("GET", r"/rest/plugins/1.0/$", load("server_plugins.json"))
    session.add("GET", r"/rest/api/2/permissionscheme$", load("server_permissionschemes.json"))
    session.add("GET", r"/rest/api/2/notificationscheme$", load("server_notificationschemes.json"))
    for key in ("plat", "ops", "legacy"):
        session.add("GET", r"/project/%s/workflowscheme$" % key.upper(), load("server_%s_workflowscheme.json" % key))
        session.add("GET", r"/project/%s/permissionscheme$" % key.upper(), load("server_%s_permissionscheme.json" % key))
        session.add("GET", r"/project/%s/notificationscheme$" % key.upper(), load("server_%s_notificationscheme.json" % key))
    return Api("https://jira.corp.example.com", session=session)


class BundleTests(unittest.TestCase):
    def test_every_audit_runs_and_keeps_only_problems(self):
        results = bundle.run_all(make_server(), cloud_apps=load("cloud_apps.json"))
        self.assertEqual(list(results), list(bundle.NAMES))
        self.assertEqual(len(results["fields"]), 1)
        self.assertEqual(len(results["users"]), 6)
        self.assertEqual([r["name"] for r in results["workflows"]], ["Old Release Flow", "Retired Hotfix Flow"])
        self.assertEqual(len(results["schemes"]), 2)
        self.assertEqual([r["filename"] for r in results["attachments"]], ["huge-export.csv", "release-build.zip", "demo.mp4"])
        self.assertEqual({r["finding"] for r in results["addons"]}, {"no-cloud-version", "disabled"})

    def test_headline(self):
        lines = bundle.headline(bundle.run_all(make_server(), cloud_apps=load("cloud_apps.json")))
        self.assertEqual([(l["audit"], l["rows"]) for l in lines],
                         [("fields", 1), ("users", 6), ("workflows", 2), ("schemes", 2), ("attachments", 3), ("addons", 2)])

    def test_a_smaller_limit_finds_more_attachments(self):
        results = bundle.run_all(make_server(), limit_mb=1)
        self.assertEqual(len(results["attachments"]), 4)


if __name__ == "__main__":
    unittest.main()
