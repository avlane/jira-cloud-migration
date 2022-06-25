import unittest

from jiramigrate import namemap
from jiramigrate.api import Api
from tests.helpers import FakeSession, load


def sites():
    server, cloud = FakeSession(), FakeSession()
    for kind, plural in (("status", "statuses"), ("issuetype", "issuetypes"), ("priority", "priorities"), ("resolution", "resolutions")):
        server.add("GET", r"/rest/api/2/%s$" % kind, load("server_%s.json" % plural))
        cloud.add("GET", r"/rest/api/3/%s$" % kind, load("cloud_%s.json" % plural))
    return (Api("https://jira.corp.example.com", session=server), Api("https://example.atlassian.net", prefix="/rest/api/3/", session=cloud))


class NameMapTests(unittest.TestCase):
    def test_statuses(self):
        rows = {(r["kind"], r["serverName"]): r["status"] for r in namemap.map_names(*sites())}
        self.assertEqual(rows[("status", "In Progress")], "matched")
        self.assertEqual(rows[("status", "Open")], "missing")
        self.assertEqual(rows[("status", "Resolved")], "missing")
        self.assertEqual(rows[("status", "Closed")], "matched")

    def test_issue_types_and_resolutions(self):
        rows = {(r["kind"], r["serverName"]): r for r in namemap.map_names(*sites())}
        self.assertEqual(rows[("issuetype", "Sub-task")]["status"], "missing")
        self.assertEqual(rows[("issuetype", "Improvement")]["status"], "missing")
        self.assertEqual(rows[("resolution", "Duplicate")]["cloudId"], "10002")
        self.assertEqual(rows[("resolution", "Fixed")]["status"], "missing")

    def test_priorities_do_not_line_up_by_name(self):
        rows = [r for r in namemap.map_names(*sites(), kinds=("priority",))]
        self.assertEqual({r["status"] for r in rows}, {"missing"})
        self.assertEqual(len(rows), 5)

    def test_case_is_ignored(self):
        rows = namemap.map_kind("status", [{"id": "1", "name": "in progress"}], [{"id": "9", "name": "In Progress"}])
        self.assertEqual((rows[0]["status"], rows[0]["cloudName"], rows[0]["cloudId"]), ("matched", "In Progress", "9"))


if __name__ == "__main__":
    unittest.main()
