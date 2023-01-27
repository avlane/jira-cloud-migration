import unittest

from jiramigrate.api import Api
from jiramigrate.validate import counts
from tests.helpers import FakeResponse, FakeSession, counts_handler, load

SERVER_COUNTS = {'project = "PLAT"': 1200, 'project = "OPS"': 845, 'project = "LEGACY"': 0}
CLOUD_COUNTS = {'project = "PLAT"': 1200, 'project = "OPS"': 840}


def sites(snapshot=False):
    server = FakeSession().add("GET", r"/rest/api/2/project$", load("server_projects.json")).add("GET", r"/rest/api/2/search$", counts_handler(SERVER_COUNTS))

    def cloud_search(call):
        jql = call["params"]["jql"]
        if "LEGACY" in jql:
            return FakeResponse(400, {"errorMessages": ["The value 'LEGACY' does not exist for the field 'project'."]})
        return counts_handler(CLOUD_COUNTS)(call)

    cloud = FakeSession().add("GET", r"/rest/api/2/search$", cloud_search)
    return (Api("https://jira.corp.example.com", session=server), server), (Api("https://example.atlassian.net", prefix="/rest/api/2/", session=cloud), cloud)


class CountTests(unittest.TestCase):
    def test_statuses(self):
        (server, _), (cloud, _) = sites()
        rows = {r["subject"]: r for r in counts.compare(server, cloud, metrics=counts.METRICS[:1])}
        self.assertEqual((rows["PLAT"]["status"], rows["PLAT"]["server"], rows["PLAT"]["cloud"]), ("ok", 1200, 1200))
        self.assertEqual((rows["OPS"]["status"], rows["OPS"]["cloud"]), ("cloud-has-fewer", 840))
        self.assertEqual((rows["LEGACY"]["status"], rows["LEGACY"]["cloud"]), ("no-project", None))

    def test_every_metric_uses_its_own_query(self):
        (server, server_session), (cloud, cloud_session) = sites()
        counts.compare(server, cloud, projects=["PLAT"])
        asked = [c["params"]["jql"] for c in cloud_session.calls]
        self.assertEqual(asked, ['project = "PLAT"', 'project = "PLAT" AND attachments is not EMPTY',
                                 'project = "PLAT" AND resolution is not EMPTY', 'project = "PLAT" AND assignee is not EMPTY'])
        self.assertEqual([c["params"]["jql"] for c in server_session.calls], asked)

    def test_snapshot_values_are_used_where_recorded(self):
        (server, server_session), (cloud, _) = sites()
        snapshot = {"projects": {"PLAT": {"issues": 1200, "withAttachments": 310}}}
        rows = counts.compare(server, cloud, snapshot=snapshot)
        by_field = {r["field"]: r for r in rows}
        self.assertEqual(by_field["withAttachments"]["server"], 310)
        self.assertEqual(len(server_session.calls), 2)  # resolved and assigned still come from the live Server

    def test_more_on_cloud(self):
        self.assertEqual(counts.row("X", "issues", 10, 12)["status"], "cloud-has-more")

    def test_explicit_projects(self):
        (server, server_session), (cloud, _) = sites()
        rows = counts.compare(server, cloud, projects=["PLAT"], metrics=counts.METRICS[:1])
        self.assertEqual([r["subject"] for r in rows], ["PLAT"])
        self.assertEqual(server_session.calls_to("GET", "/project"), [])

    def test_a_snapshot_replaces_live_server_counts(self):
        (server, server_session), (cloud, _) = sites()
        snapshot = {"projects": {"PLAT": {"issues": 1210}, "OPS": {"issues": 840}}}
        rows = {r["subject"]: r for r in counts.compare(server, cloud, snapshot=snapshot, metrics=counts.METRICS[:1])}
        self.assertEqual(sorted(rows), ["OPS", "PLAT"])
        self.assertEqual((rows["PLAT"]["server"], rows["PLAT"]["status"]), (1210, "cloud-has-fewer"))
        self.assertEqual(rows["OPS"]["status"], "ok")
        self.assertEqual(server_session.calls, [])

    def test_other_cloud_errors_are_not_swallowed(self):
        from jiramigrate.api import ApiError
        (server, _), (cloud, cloud_session) = sites()
        cloud_session.routes.clear()
        cloud_session.add("GET", r"/search$", FakeResponse(500, "boom"))
        with self.assertRaises(ApiError):
            counts.compare(server, cloud, projects=["PLAT"], metrics=counts.METRICS[:1])


if __name__ == "__main__":
    unittest.main()
