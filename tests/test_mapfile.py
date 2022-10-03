import os
import tempfile
import unittest
from datetime import datetime, timezone

from jiramigrate import mapfile

ROWS = [{"serverName": "a", "status": "matched"}, {"serverName": "b", "status": "missing"}, {"serverName": "c", "status": "matched"}]


class MapFileTests(unittest.TestCase):
    def test_build(self):
        data = mapfile.build("users", ROWS, "https://jira.corp.example.com", "https://example.atlassian.net",
                             now=datetime(2022, 10, 2, 9, 0, tzinfo=timezone.utc))
        self.assertEqual(data["version"], 1)
        self.assertEqual(data["generated"], "2022-10-02T09:00:00+00:00")
        self.assertEqual(data["summary"], {"matched": 2, "missing": 1})
        self.assertEqual(data["items"], ROWS)

    def test_round_trip_and_kind_check(self):
        data = mapfile.build("fields", ROWS, "s", "c")
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "fields.json")
            mapfile.write(path, data)
            self.assertEqual(mapfile.read(path, "fields"), data)
            with self.assertRaises(ValueError):
                mapfile.read(path, "users")

    def test_unknown_kind_and_version(self):
        with self.assertRaises(ValueError):
            mapfile.build("colours", [], "s", "c")
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "x.json")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write('{"version": 3}')
            with self.assertRaises(ValueError):
                mapfile.read(path)


if __name__ == "__main__":
    unittest.main()
