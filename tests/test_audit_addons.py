import unittest

from jiramigrate.api import Api
from jiramigrate.audit import addons
from tests.helpers import FakeSession, load


def make_server():
    session = FakeSession().add("GET", r"/rest/plugins/1.0/$", load("server_plugins.json"))
    return Api("https://jira.corp.example.com", session=session), session


class AddonTests(unittest.TestCase):
    def test_only_user_installed_apps(self):
        server, session = make_server()
        keys = [p["key"] for p in addons.installed_apps(server)]
        self.assertEqual(keys, ["com.example.timesheet", "com.example.scriptrunner", "com.example.legacy-report", "com.example.theme"])
        self.assertTrue(session.calls[0]["url"].endswith("/rest/plugins/1.0/"))

    def test_inventory_rows_sorted_by_name(self):
        server, _ = make_server()
        rows = addons.inventory(server)
        self.assertEqual([r["name"] for r in rows], ["Corporate Theme", "Legacy Reports", "Script Console", "Timesheet for Jira"])
        self.assertEqual((rows[3]["version"], rows[3]["vendor"], rows[3]["licensed"]), ("4.2.1", "Example Apps", True))
        self.assertFalse(rows[1]["enabled"])


if __name__ == "__main__":
    unittest.main()
