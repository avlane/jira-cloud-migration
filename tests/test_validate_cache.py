import os
import tempfile
import unittest

from jiramigrate.api import Api
from jiramigrate.validate import sample
from jiramigrate.validate.cache import JsonCache
from tests.helpers import FakeSession, load
from tests.test_validate_run import make_site


class CacheTests(unittest.TestCase):
    def test_round_trip_and_odd_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = JsonCache(os.path.join(tmp, "nested", "cache"))
            self.assertIsNone(cache.get("issue-PLAT-1"))
            cache.set("issue-PLAT-1", {"a": [1, 2]})
            self.assertEqual(cache.get("issue-PLAT-1"), {"a": [1, 2]})
            cache.set("../escape/key", {"b": 1})
            self.assertEqual(cache.get("../escape/key"), {"b": 1})
            self.assertEqual(sorted(os.listdir(os.path.join(tmp, "nested", "cache"))), [".._escape_key.json", "issue-PLAT-1.json"])

    def test_corrupt_files_count_as_misses(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = JsonCache(tmp)
            with open(cache.path("k"), "w", encoding="utf-8") as handle:
                handle.write("{broken")
            self.assertIsNone(cache.get("k"))

    def test_second_fetch_uses_the_cache(self):
        issues = {i["key"]: i for i in load("sample_server_issues.json") if i["key"].startswith("PLAT")}
        api = make_site(issues, "https://jira.corp.example.com")
        with tempfile.TemporaryDirectory() as tmp:
            cache = JsonCache(tmp)
            first = sample.fetch_issues(api, ["PLAT-1", "PLAT-2"], cache=cache)
            calls = len(api.session.calls)
            second = sample.fetch_issues(api, ["PLAT-1", "PLAT-2", "PLAT-3"], cache=cache)
            self.assertEqual(len(api.session.calls), calls + 1)
            self.assertEqual(sorted(second), ["PLAT-1", "PLAT-2", "PLAT-3"])
            self.assertEqual(first["PLAT-1"], second["PLAT-1"])
            only_new = api.session.calls[-1]["params"]["jql"]
            self.assertEqual(only_new, "key in (PLAT-3)")

    def test_a_different_field_list_invalidates_the_entry(self):
        issues = {i["key"]: i for i in load("sample_server_issues.json") if i["key"].startswith("PLAT")}
        api = make_site(issues, "https://jira.corp.example.com")
        with tempfile.TemporaryDirectory() as tmp:
            cache = JsonCache(tmp)
            sample.fetch_issues(api, ["PLAT-1"], fields=("summary",), cache=cache)
            sample.fetch_issues(api, ["PLAT-1"], fields=("summary", "status"), cache=cache)
            self.assertEqual(len(api.session.calls), 2)


if __name__ == "__main__":
    unittest.main()
