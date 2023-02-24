import unittest

from jiramigrate.validate import diff
from tests.helpers import load


def issues():
    server = {i["key"]: i for i in load("sample_server_issues.json")}
    cloud = {i["key"]: i for i in load("sample_cloud_issues.json")}
    return server, cloud


def context():
    return diff.Context(users=load("sample_users.json"), names=load("sample_names.json"))


class ScalarTests(unittest.TestCase):
    def test_translated_names_are_not_differences(self):
        server, cloud = issues()
        self.assertEqual(diff.scalar_diffs(server["PLAT-1"], cloud["PLAT-1"], context()), [])
        self.assertEqual(diff.scalar_diffs(server["PLAT-2"], cloud["PLAT-2"], context()), [])

    def test_without_the_mapping_the_same_issues_differ(self):
        server, cloud = issues()
        found = diff.scalar_diffs(server["PLAT-1"], cloud["PLAT-1"], diff.Context())
        self.assertEqual([(d["field"], d["server"], d["cloud"]) for d in found], [("status", "Open", "To Do"), ("priority", "Major", "Medium")])

    def test_a_real_difference(self):
        server, cloud = issues()
        cloud["PLAT-3"]["fields"]["summary"] = "Upgrade the build image"
        cloud["PLAT-3"]["fields"]["status"] = {"name": "In Progress"}
        found = diff.scalar_diffs(server["PLAT-3"], cloud["PLAT-3"], context())
        self.assertEqual([(d["subject"], d["field"], d["server"], d["cloud"], d["status"]) for d in found],
                         [("PLAT-3", "summary", "Upgrade build image", "Upgrade the build image", "differs"),
                          ("PLAT-3", "status", "To Do", "In Progress", "differs")])

    def test_missing_resolution_on_one_side(self):
        server, cloud = issues()
        cloud["PLAT-2"]["fields"]["resolution"] = None
        found = diff.scalar_diffs(server["PLAT-2"], cloud["PLAT-2"], context())
        self.assertEqual([(d["field"], d["server"], d["cloud"]) for d in found], [("resolution", "Done", "")])

    def test_surrounding_whitespace_in_summaries_is_ignored(self):
        server, cloud = issues()
        cloud["PLAT-1"]["fields"]["summary"] = "  Login times out "
        self.assertEqual(diff.scalar_diffs(server["PLAT-1"], cloud["PLAT-1"], context()), [])


if __name__ == "__main__":
    unittest.main()
