import unittest

from jiramigrate.api import Api
from jiramigrate.validate import diff, run, summary
from tests.helpers import FakeSession, load
from tests.test_validate_diff import context

SERVER = {i["key"]: i for i in load("sample_server_issues.json")}
CLOUD = {i["key"]: i for i in load("sample_cloud_issues.json")}


def keys_in(call):
    jql = call["params"]["jql"]
    return [k.strip() for k in jql[jql.index("(") + 1:jql.rindex(")")].split(",")]


def make_site(issues, base):
    def handler(call):
        jql = call["params"]["jql"]
        if "ORDER BY" in jql:  # newest or oldest issue (keys are numbered in creation order)
            pick = max if ("DESC" in jql) else min
            top = pick(issues, key=lambda k: int(k.rsplit("-", 1)[1]))
            return {"total": 1, "issues": [{"key": top, "fields": {}}]}
        found = [issues[k] for k in keys_in(call) if k in issues]
        return {"startAt": 0, "maxResults": 100, "total": len(found), "issues": found}
    session = FakeSession().add("GET", r"/rest/api/2/search$", handler)
    return Api(base, prefix="/rest/api/2/", session=session)


class RunTests(unittest.TestCase):
    def test_sample_of_a_project(self):
        server = make_site({k: v for k, v in SERVER.items() if k.startswith("PLAT")}, "https://jira.corp.example.com")
        cloud = make_site({k: v for k, v in CLOUD.items() if k.startswith("PLAT")}, "https://example.atlassian.net")
        rows, keys = run.compare_sample(server, cloud, "PLAT", 10, 1, context())
        self.assertEqual(keys, ["PLAT-1", "PLAT-2", "PLAT-3"])
        self.assertEqual({(r["subject"], r["field"]) for r in rows},
                         {("PLAT-2", "link"), ("PLAT-3", "description"), ("PLAT-3", "comments"), ("PLAT-3", "attachments"), ("PLAT-3", "attachment bytes")})


    def test_an_issue_missing_on_cloud_is_a_finding_not_a_crash(self):
        server = make_site({k: v for k, v in SERVER.items() if k.startswith("OPS")}, "https://jira.corp.example.com")
        cloud = make_site({k: v for k, v in CLOUD.items() if k.startswith("OPS") and k != "OPS-2"}, "https://example.atlassian.net")
        rows, keys = run.compare_sample(server, cloud, "OPS", 10, 1, context())
        self.assertEqual(keys, ["OPS-1", "OPS-2"])
        missing = [r for r in rows if r["status"] == "missing-on-cloud"]
        self.assertEqual([(r["subject"], r["field"], r["cloud"]) for r in missing], [("OPS-2", "issue", "(not found)")])
        self.assertEqual(summary.exit_code(missing), 1)

    def test_issues_that_vanished_from_the_server_are_skipped(self):
        server = make_site({"PLAT-1": SERVER["PLAT-1"]}, "https://jira.corp.example.com")
        original = server.session.routes[0]
        calls = []

        def flaky(call):
            calls.append(call)
            if "ORDER BY" not in call["params"]["jql"] and len(calls) > 3:
                return {"startAt": 0, "maxResults": 100, "total": 0, "issues": []}
            return original[2](call)

        server.session.routes[0] = (original[0], original[1], flaky)
        cloud = make_site(CLOUD, "https://example.atlassian.net")
        rows, keys = run.compare_sample(server, cloud, "PLAT", 3, 1, context())
        self.assertEqual(rows, [])


class SummaryTests(unittest.TestCase):
    ROWS = [
        {"check": "count", "subject": "PLAT", "field": "issues", "status": "ok"},
        {"check": "count", "subject": "OPS", "field": "issues", "status": "cloud-has-fewer"},
        {"check": "sample", "subject": "PLAT-3", "field": "description", "status": "differs"},
        {"check": "sample", "subject": "PLAT-3", "field": "comments", "status": "differs"},
        {"check": "sample", "subject": "OPS-1", "field": "reporter", "status": "unmapped-user"},
    ]

    def test_numbers(self):
        got = summary.summarize(self.ROWS, sampled=12)
        self.assertEqual(got, {"countChecks": 2, "countProblems": 1, "sampledIssues": 12, "issuesWithDifferences": 1, "warnings": 1, "problems": 3})

    def test_description(self):
        lines = summary.describe(summary.summarize(self.ROWS, sampled=12))
        self.assertEqual(lines, ["counts: 2 compared, 1 differ", "sample: 12 issues checked, 1 with differences",
                                 "warnings: 1 (users missing from the mapping)", "result: FAIL (3 problems)"])

    def test_pass(self):
        rows = [r for r in self.ROWS if r["status"] in ("ok", "unmapped-user")]
        self.assertEqual(summary.exit_code(rows), 0)
        self.assertEqual(summary.describe(summary.summarize(rows))[-1], "result: PASS")
        self.assertEqual(summary.exit_code(self.ROWS), 1)

    def test_strict_mode_fails_on_warnings(self):
        rows = [r for r in self.ROWS if r["status"] in ("ok", "unmapped-user")]
        self.assertEqual(summary.exit_code(rows), 0)
        self.assertEqual(summary.exit_code(rows, strict=True), 1)
        self.assertEqual(summary.exit_code([r for r in rows if r["status"] == "ok"], strict=True), 0)

    def test_nothing_checked_passes(self):
        self.assertEqual(summary.describe(summary.summarize([])), ["result: PASS"])


if __name__ == "__main__":
    unittest.main()
