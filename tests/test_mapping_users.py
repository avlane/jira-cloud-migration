import unittest

from jiramigrate import mapping
from jiramigrate.api import Api
from tests.helpers import FakeSession, load


def make_cloud():
    results = load("cloud_user_search.json")
    session = FakeSession().add("GET", r"/rest/api/3/user/search$", lambda call: results.get(call["params"]["query"].lower(), []))
    return Api("https://example.atlassian.net", auth=("ops@example.com", "tok"), prefix="/rest/api/3/", session=session), session


class UserMappingTests(unittest.TestCase):
    def users(self):
        return {u["name"]: u for u in load("server_users.json")}

    def test_exact_email_match(self):
        cloud, session = make_cloud()
        row = mapping.map_user(cloud, self.users()["amoreau"])
        self.assertEqual((row["status"], row["accountId"], row["cloudName"]), ("matched", "5b10ac8d82e05b22cc7d4ef5", "Alice Moreau"))
        self.assertEqual((row["serverKey"], row["serverName"]), ("JIRAUSER10100", "amoreau"))
        self.assertEqual(session.calls[0]["params"]["query"], "alice.moreau@example.com")

    def test_case_differences_still_match(self):
        cloud, _ = make_cloud()
        row = mapping.map_user(cloud, {"name": "ec", "key": "k", "emailAddress": "Erin.Castellano@Example.com"})
        self.assertEqual(row["status"], "matched")

    def test_unknown_email_is_missing(self):
        cloud, _ = make_cloud()
        self.assertEqual(mapping.map_user(cloud, self.users()["tmp-user"])["status"], "missing")

    def test_no_email_means_no_request(self):
        cloud, session = make_cloud()
        row = mapping.map_user(cloud, self.users()["svc-build"])
        self.assertEqual(row["status"], "missing")
        self.assertEqual(session.calls, [])


if __name__ == "__main__":
    unittest.main()
