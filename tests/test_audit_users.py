import unittest

from jiramigrate.api import Api
from jiramigrate.audit import users
from tests.helpers import FakeSession, load, paged


def make_server(cap=None):
    session = FakeSession().add("GET", r"/rest/api/2/user/search$", paged(load("server_users.json"), cap=cap))
    return Api("https://jira.corp.example.com", session=session), session


class UserAuditTests(unittest.TestCase):
    def test_fetches_everyone_including_inactive(self):
        server, session = make_server(cap=4)
        got = users.all_users(server)
        self.assertEqual(len(got), 9)
        params = session.calls[0]["params"]
        self.assertEqual((params["username"], params["includeInactive"]), (".", "true"))

    def test_findings(self):
        server, _ = make_server()
        rows = {r["name"]: r["findings"] for r in users.audit(users.all_users(server))}
        self.assertEqual(rows["amoreau"], [])
        self.assertEqual(rows["svc-build"], ["no-email"])
        self.assertEqual(rows["frank"], ["no-email"])
        self.assertEqual(rows["tmp-user"], ["invalid-email"])
        self.assertEqual(rows["dwhitfield"], ["inactive"])

    def test_duplicate_emails_ignore_case(self):
        server, _ = make_server()
        rows = {r["name"]: r["findings"] for r in users.audit(users.all_users(server))}
        self.assertEqual(rows["econtractor"], ["duplicate-email"])
        self.assertEqual(rows["ecastellano"], ["duplicate-email"])

    def test_rows_carry_the_server_key(self):
        server, _ = make_server()
        row = users.audit(users.all_users(server))[0]
        self.assertEqual((row["key"], row["email"]), ("JIRAUSER10100", "alice.moreau@example.com"))


if __name__ == "__main__":
    unittest.main()
