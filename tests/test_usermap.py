import unittest

from jiramigrate import usermap
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
        row = usermap.map_user(cloud, self.users()["amoreau"])
        self.assertEqual((row["status"], row["accountId"], row["cloudName"]), ("matched", "5b10ac8d82e05b22cc7d4ef5", "Alice Moreau"))
        self.assertEqual((row["serverKey"], row["serverName"]), ("JIRAUSER10100", "amoreau"))
        self.assertEqual(session.calls[0]["params"]["query"], "alice.moreau@example.com")

    def test_case_differences_still_match(self):
        cloud, _ = make_cloud()
        row = usermap.map_user(cloud, {"name": "ec", "key": "k", "emailAddress": "Erin.Castellano@Example.com"})
        self.assertEqual(row["status"], "matched")

    def test_unknown_email_is_missing(self):
        cloud, _ = make_cloud()
        self.assertEqual(usermap.map_user(cloud, self.users()["tmp-user"])["status"], "missing")

    def test_no_email_means_no_request(self):
        cloud, session = make_cloud()
        row = usermap.map_user(cloud, self.users()["svc-build"])
        self.assertEqual(row["status"], "no-email")
        self.assertEqual(session.calls, [])


class MappingStatusTests(unittest.TestCase):
    def users(self):
        return {u["name"]: u for u in load("server_users.json")}

    def test_hidden_email_single_result_is_probable(self):
        cloud, _ = make_cloud()
        row = usermap.map_user(cloud, self.users()["cnguyen"])
        self.assertEqual((row["status"], row["accountId"]), ("probable", "712020:6f1d2a3b-4c5d-4e6f-8a9b-0c1d2e3f4a5b"))
        self.assertIn("confirm by name", row["note"])

    def test_several_hidden_candidates_are_ambiguous(self):
        results = {"g@example.com": [{"accountId": "a", "displayName": "G One", "accountType": "atlassian", "active": True},
                                     {"accountId": "b", "displayName": "G Two", "accountType": "atlassian", "active": True}]}
        session = FakeSession().add("GET", r"/user/search$", lambda call: results[call["params"]["query"]])
        cloud = Api("https://example.atlassian.net", prefix="/rest/api/3/", session=session)
        row = usermap.map_user(cloud, {"name": "g", "key": "g", "emailAddress": "g@example.com"})
        self.assertEqual((row["status"], row["accountId"]), ("ambiguous", ""))

    def test_two_visible_matches_are_ambiguous(self):
        both = [{"accountId": "a", "emailAddress": "x@example.com", "accountType": "atlassian"}, {"accountId": "b", "emailAddress": "X@example.com", "accountType": "atlassian"}]
        session = FakeSession().add("GET", r"/user/search$", both)
        cloud = Api("https://example.atlassian.net", prefix="/rest/api/3/", session=session)
        self.assertEqual(usermap.map_user(cloud, {"name": "x", "emailAddress": "x@example.com"})["status"], "ambiguous")

    def test_apps_and_customers_are_not_candidates(self):
        found = [{"accountId": "bot", "emailAddress": "x@example.com", "accountType": "app"}]
        session = FakeSession().add("GET", r"/user/search$", found)
        cloud = Api("https://example.atlassian.net", prefix="/rest/api/3/", session=session)
        self.assertEqual(usermap.map_user(cloud, {"name": "x", "emailAddress": "x@example.com"})["status"], "missing")

    def test_deactivated_cloud_accounts_are_noted(self):
        cloud, _ = make_cloud()
        row = usermap.map_user(cloud, self.users()["dwhitfield"])
        self.assertEqual(row["status"], "matched")
        self.assertIn("deactivated", row["note"])

    def test_no_email_status(self):
        cloud, _ = make_cloud()
        self.assertEqual(usermap.map_user(cloud, self.users()["frank"])["status"], "no-email")

    def test_shared_email_goes_to_the_first_account_only(self):
        cloud, _ = make_cloud()
        rows = {r["serverName"]: r for r in usermap.map_users(cloud, load("server_users.json"))}
        self.assertEqual(rows["econtractor"]["status"], "matched")
        self.assertEqual(rows["ecastellano"]["status"], "duplicate")
        self.assertEqual(rows["ecastellano"]["note"], "same email as econtractor")
        self.assertEqual(rows["ecastellano"]["accountId"], "")

    def test_summary_and_mention_table(self):
        cloud, _ = make_cloud()
        rows = usermap.map_users(cloud, load("server_users.json"))
        self.assertEqual(usermap.summary(rows), {"matched": 4, "probable": 1, "no-email": 2, "duplicate": 1, "missing": 1})
        names = usermap.mention_names(rows)
        self.assertEqual(names["amoreau"], "5b10ac8d82e05b22cc7d4ef5")
        self.assertNotIn("ecastellano", names)
        self.assertNotIn("frank", names)

    def test_summary_of_the_fixture(self):
        cloud, _ = make_cloud()
        statuses = {r["serverName"]: r["status"] for r in usermap.map_users(cloud, load("server_users.json"))}
        self.assertEqual(statuses, {"amoreau": "matched", "bokafor": "matched", "cnguyen": "probable", "dwhitfield": "matched",
                                    "svc-build": "no-email", "econtractor": "matched", "ecastellano": "duplicate", "frank": "no-email", "tmp-user": "missing"})


if __name__ == "__main__":
    unittest.main()
