import unittest

from jiramigrate.api import Api
from jiramigrate.validate import sample
from tests.helpers import FakeSession

EXISTING = {"PLAT-%d" % n for n in range(1, 41)} - {"PLAT-7", "PLAT-8", "PLAT-9", "PLAT-20"}


def jql_search(call):
    """A tiny JQL-aware search: the newest key, or key in (...)."""
    jql = call["params"]["jql"]
    if "ORDER BY key DESC" in jql:
        return {"startAt": 0, "maxResults": 1, "total": 1, "issues": [{"key": "PLAT-40", "fields": {}}]}
    wanted = [k.strip() for k in jql[jql.index("(") + 1:jql.rindex(")")].split(",")]
    issues = [{"key": k, "fields": {"summary": k}} for k in wanted if k in EXISTING]
    return {"startAt": 0, "maxResults": 100, "total": len(issues), "issues": issues}


def make_server():
    session = FakeSession().add("GET", r"/rest/api/2/search$", jql_search)
    return Api("https://jira.corp.example.com", session=session), session


class PickKeysTests(unittest.TestCase):
    def test_same_seed_same_keys(self):
        server, _ = make_server()
        first = sample.pick_keys(server, "PLAT", 10, seed=7)
        again = sample.pick_keys(make_server()[0], "PLAT", 10, seed=7)
        other = sample.pick_keys(make_server()[0], "PLAT", 10, seed=8)
        self.assertEqual(first, again)
        self.assertNotEqual(first, other)

    def test_keys_exist_and_are_sorted_by_number(self):
        server, _ = make_server()
        keys = sample.pick_keys(server, "PLAT", 10, seed=1)
        self.assertEqual(len(keys), 10)
        self.assertTrue(set(keys) <= EXISTING)
        self.assertEqual(keys, sorted(keys, key=sample.key_number))
        self.assertEqual(len(set(keys)), 10)

    def test_small_projects_return_what_exists(self):
        server, _ = make_server()
        keys = sample.pick_keys(server, "PLAT", 100, seed=1)
        self.assertEqual(set(keys), EXISTING)

    def test_empty_project(self):
        session = FakeSession().add("GET", r"/search$", {"startAt": 0, "maxResults": 1, "total": 0, "issues": []})
        self.assertEqual(sample.pick_keys(Api("https://jira.corp.example.com", session=session), "EMPTY", 5, seed=1), [])

    def test_fetch_issues_batches_by_fifty(self):
        server, session = make_server()
        got = sample.fetch_issues(server, ["PLAT-%d" % n for n in range(1, 121)])
        self.assertEqual(len(got), 36)
        self.assertEqual(len(session.calls), 3)
        self.assertEqual(session.calls[0]["params"]["fields"], ",".join(sample.FIELDS))


if __name__ == "__main__":
    unittest.main()
