import unittest

from jiramigrate.api import Api
from jiramigrate.audit import workflows
from tests.helpers import FakeSession, load


def make_server():
    session = FakeSession()
    session.add("GET", r"/rest/api/2/project$", load("server_projects.json"))
    session.add("GET", r"/rest/api/2/workflow$", load("server_workflows.json"))
    session.add("GET", r"/project/PLAT/workflowscheme$", load("server_plat_workflowscheme.json"))
    session.add("GET", r"/project/OPS/workflowscheme$", load("server_ops_workflowscheme.json"))
    session.add("GET", r"/project/LEGACY/workflowscheme$", load("server_legacy_workflowscheme.json"))
    return Api("https://jira.corp.example.com", session=session), session


class WorkflowAuditTests(unittest.TestCase):
    def test_scheme_workflows_include_mappings(self):
        scheme = load("server_plat_workflowscheme.json")
        self.assertEqual(workflows.scheme_workflows(scheme), {"PLAT Workflow", "PLAT Bug Workflow"})

    def test_unused_workflows(self):
        server, _ = make_server()
        rows = {r["name"]: r for r in workflows.report(server)}
        self.assertEqual(rows["PLAT Workflow"]["projects"], ["PLAT"])
        self.assertEqual(rows["jira"]["projects"], ["LEGACY"])
        self.assertEqual(rows["Old Release Flow"]["finding"], "unused")
        self.assertEqual(rows["Retired Hotfix Flow"]["finding"], "unused")
        self.assertEqual(sum(1 for r in rows.values() if r["finding"]), 2)

    def test_default_workflow_is_never_flagged(self):
        server, session = make_server()
        session.routes = [r for r in session.routes if "LEGACY" not in r[1].pattern]
        session.add("GET", r"/project/LEGACY/workflowscheme$", {"name": "Other", "defaultWorkflow": "PLAT Workflow", "issueTypeMappings": {}})
        rows = {r["name"]: r for r in workflows.report(server)}
        self.assertEqual(rows["jira"]["projects"], [])
        self.assertEqual(rows["jira"]["finding"], "")

    def test_one_scheme_lookup_per_project(self):
        server, session = make_server()
        workflows.report(server)
        self.assertEqual(len(session.calls_to("GET", "workflowscheme")), 3)


if __name__ == "__main__":
    unittest.main()
