import os
import tempfile
import unittest
from datetime import datetime, timezone

from jiramigrate import snapshot
from jiramigrate.api import Api
from tests.helpers import FakeSession, load

COUNTS = {"PLAT": (1200, 310), "OPS": (845, 60), "LEGACY": (0, 0)}
UPDATED = {"PLAT": "2022-03-11T17:02:44.000+0000", "OPS": "2022-03-12T08:30:00.000+0000"}


def search(call):
    q = call["params"]
    key = q["jql"].split('"')[1]
    withAtt = "attachments is not EMPTY" in q["jql"]
    if int(q["maxResults"]) == 0:
        total = COUNTS[key][1] if withAtt else COUNTS[key][0]
        return {"startAt": 0, "maxResults": 0, "total": total, "issues": []}
    issues = [{"id": "1", "key": key + "-1", "fields": {"updated": UPDATED[key]}}] if key in UPDATED else []
    return {"startAt": 0, "maxResults": 1, "total": len(issues), "issues": issues}


def make_server():
    session = FakeSession().add("GET", r"/rest/api/2/project$", load("server_projects.json")).add("GET", r"/rest/api/2/search$", search)
    return Api("https://jira.corp.example.com", session=session), session


class SnapshotTests(unittest.TestCase):
    def test_counts_per_project(self):
        server, _ = make_server()
        snap = snapshot.take(server, now=datetime(2022, 3, 13, 20, 0, tzinfo=timezone.utc))
        self.assertEqual(snap["taken"], "2022-03-13T20:00:00+00:00")
        self.assertEqual(snap["server"], "https://jira.corp.example.com")
        self.assertEqual(snap["projects"]["PLAT"], {"name": "Platform", "issues": 1200, "withAttachments": 310, "lastUpdated": "2022-03-11T17:02:44.000+0000"})
        self.assertEqual(snap["projects"]["LEGACY"]["issues"], 0)
        self.assertIsNone(snap["projects"]["LEGACY"]["lastUpdated"])

    def test_save_and_load(self):
        server, _ = make_server()
        snap = snapshot.take(server)
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "snap.json")
            snapshot.save(path, snap)
            self.assertEqual(snapshot.load(path), snap)

    def test_wrong_version_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "snap.json")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write('{"version": 7}')
            with self.assertRaises(ValueError):
                snapshot.load(path)


if __name__ == "__main__":
    unittest.main()
