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


class PeopleAndSetTests(unittest.TestCase):
    def test_mapped_people_match_by_account_id(self):
        server, cloud = issues()
        self.assertEqual(diff.people_diffs(server["PLAT-1"], cloud["PLAT-1"], context()), [])

    def test_unassigned_on_both_sides(self):
        server, cloud = issues()
        self.assertEqual([d["field"] for d in diff.people_diffs(server["PLAT-3"], cloud["PLAT-3"], context())], [])

    def test_wrong_assignee(self):
        server, cloud = issues()
        found = diff.people_diffs(server["OPS-1"], cloud["OPS-1"], context())
        assignee = [d for d in found if d["field"] == "assignee"][0]
        self.assertEqual((assignee["server"], assignee["cloud"], assignee["status"]), (m_ca3(), m_ca1(), "differs"))

    def test_unmapped_users_are_flagged_separately(self):
        server, cloud = issues()
        found = diff.people_diffs(server["OPS-1"], cloud["OPS-1"], context())
        reporter = [d for d in found if d["field"] == "reporter"][0]
        self.assertEqual((reporter["server"], reporter["status"]), ("svc-build", "unmapped-user"))

    def test_assignee_dropped_during_migration(self):
        server, cloud = issues()
        cloud["PLAT-1"]["fields"]["assignee"] = None
        found = diff.people_diffs(server["PLAT-1"], cloud["PLAT-1"], context())
        self.assertEqual([(d["field"], d["cloud"]) for d in found], [("assignee", "(none)")])

    def test_sets(self):
        server, cloud = issues()
        self.assertEqual(diff.set_diffs(server["PLAT-1"], cloud["PLAT-1"]), [])
        found = diff.set_diffs(server["OPS-1"], cloud["OPS-1"])
        self.assertEqual([(d["field"], d["server"], d["cloud"]) for d in found], [("labels", "urgent, vip", "vip")])

    def test_components_and_versions(self):
        server, cloud = issues()
        cloud["PLAT-1"]["fields"]["components"] = []
        cloud["PLAT-1"]["fields"]["fixVersions"] = [{"name": "2.16"}]
        fields = {d["field"]: d for d in diff.set_diffs(server["PLAT-1"], cloud["PLAT-1"])}
        self.assertEqual((fields["components"]["server"], fields["components"]["cloud"]), ("Web", ""))
        self.assertEqual((fields["fixVersions"]["server"], fields["fixVersions"]["cloud"]), ("2.15", "2.16"))

    def test_compare_issue_combines_everything(self):
        server, cloud = issues()
        self.assertEqual(diff.compare_issue(server["PLAT-1"], cloud["PLAT-1"], context()), [])
        self.assertEqual({d["field"] for d in diff.compare_issue(server["OPS-1"], cloud["OPS-1"], context())}, {"assignee", "reporter", "labels"})
        self.assertEqual({d["field"] for d in diff.compare_issue(server["PLAT-3"], cloud["PLAT-3"], context())},
                         {"description", "comments", "attachments", "attachment bytes"})
        self.assertEqual({d["field"] for d in diff.compare_issue(server["PLAT-2"], cloud["PLAT-2"], context())}, {"link"})


class TimeTests(unittest.TestCase):
    def test_no_time_logged_on_either_side(self):
        server, cloud = issues()
        self.assertEqual(diff.time_diffs(server["PLAT-1"], cloud["PLAT-1"]), [])

    def test_logged_time_that_did_not_arrive(self):
        server, cloud = issues()
        server["PLAT-1"]["fields"]["timespent"] = 28800
        server["PLAT-1"]["fields"]["timeoriginalestimate"] = 14400
        cloud["PLAT-1"]["fields"]["timespent"] = 25200
        cloud["PLAT-1"]["fields"]["timeoriginalestimate"] = 14400
        found = diff.time_diffs(server["PLAT-1"], cloud["PLAT-1"])
        self.assertEqual([(d["field"], d["server"], d["cloud"]) for d in found], [("time spent (s)", 28800, 25200)])

    def test_none_and_zero_are_the_same(self):
        server, cloud = issues()
        server["PLAT-2"]["fields"]["timespent"] = None
        cloud["PLAT-2"]["fields"]["timespent"] = 0
        self.assertEqual(diff.time_diffs(server["PLAT-2"], cloud["PLAT-2"]), [])


class LinkTests(unittest.TestCase):
    def test_matching_links(self):
        server, cloud = issues()
        self.assertEqual(diff.link_diffs(server["PLAT-1"], cloud["PLAT-1"]), [])
        self.assertEqual(diff.link_signatures(server["PLAT-3"]), {"is blocked by PLAT-1"})

    def test_link_lost_in_migration(self):
        server, cloud = issues()
        found = diff.link_diffs(server["PLAT-2"], cloud["PLAT-2"])
        self.assertEqual([(d["field"], d["server"], d["cloud"], d["status"]) for d in found], [("link", "relates to OPS-1", "(missing)", "missing-link")])

    def test_extra_link_on_cloud(self):
        server, cloud = issues()
        cloud["OPS-1"]["fields"]["issuelinks"] = [{"type": {"name": "Blocks", "inward": "is blocked by", "outward": "blocks"}, "inwardIssue": {"key": "OPS-9"}}]
        found = diff.link_diffs(server["OPS-1"], cloud["OPS-1"])
        self.assertEqual([(d["server"], d["cloud"], d["status"]) for d in found], [("(none)", "is blocked by OPS-9", "extra-link")])

    def test_a_link_pointing_the_other_way_is_a_difference(self):
        server, cloud = issues()
        cloud["PLAT-1"]["fields"]["issuelinks"] = [{"type": {"name": "Blocks", "inward": "is blocked by", "outward": "blocks"}, "inwardIssue": {"key": "PLAT-3"}}]
        found = diff.link_diffs(server["PLAT-1"], cloud["PLAT-1"])
        self.assertEqual({d["status"] for d in found}, {"missing-link", "extra-link"})


class CountTests(unittest.TestCase):
    def test_equal_counts(self):
        server, cloud = issues()
        self.assertEqual(diff.count_diffs(server["PLAT-1"], cloud["PLAT-1"]), [])

    def test_missing_comment_and_attachment(self):
        server, cloud = issues()
        found = diff.count_diffs(server["PLAT-3"], cloud["PLAT-3"])
        self.assertEqual([(d["field"], d["server"], d["cloud"]) for d in found], [("comments", 3, 2), ("attachments", 2, 1), ("attachment bytes", 350, 100)])

    def test_same_count_but_a_smaller_file(self):
        server, cloud = issues()
        cloud["PLAT-1"]["fields"]["attachment"][0]["size"] = 100
        found = diff.count_diffs(server["PLAT-1"], cloud["PLAT-1"])
        self.assertEqual([d["field"] for d in found], ["attachment bytes"])

    def test_issue_without_comment_block(self):
        self.assertEqual(diff.count_diffs({"key": "A-1", "fields": {}}, {"key": "A-1", "fields": {}}), [])


class TextTests(unittest.TestCase):
    def test_line_endings_and_mentions_are_normalised(self):
        server, cloud = issues()
        self.assertEqual(diff.text_diffs(server["PLAT-1"], cloud["PLAT-1"], context()), [])

    def test_without_the_user_mapping_mentions_differ(self):
        server, cloud = issues()
        found = diff.text_diffs(server["PLAT-1"], cloud["PLAT-1"], diff.Context())
        self.assertEqual([d["field"] for d in found], ["description", "comment 2"])

    def test_changed_description(self):
        server, cloud = issues()
        found = diff.text_diffs(server["PLAT-3"], cloud["PLAT-3"], context())
        self.assertEqual(len(found), 1)
        self.assertEqual((found[0]["field"], found[0]["server"], found[0]["cloud"]), ("description", "Move to the new base image. See the runbook.", "Move to the new base image."))
        self.assertTrue(found[0]["note"].startswith("similarity 0."))

    def test_extra_comments_are_left_to_the_count_check(self):
        server, cloud = issues()
        self.assertEqual([d for d in diff.text_diffs(server["PLAT-3"], cloud["PLAT-3"], context()) if d["field"].startswith("comment")], [])

    def test_changed_comment(self):
        server, cloud = issues()
        cloud["PLAT-1"]["fields"]["comment"]["comments"][0]["body"] = "Seen on staging."
        found = diff.text_diffs(server["PLAT-1"], cloud["PLAT-1"], context())
        self.assertEqual([d["field"] for d in found], ["comment 1"])

    def test_long_text_is_cut_in_the_report(self):
        found = diff.text_diffs({"key": "A-1", "fields": {"description": "word " * 40}}, {"key": "A-1", "fields": {"description": "other"}}, diff.Context())
        self.assertEqual(len(found[0]["server"]), 60)
        self.assertTrue(found[0]["server"].endswith("..."))

    def test_normalise_text(self):
        ctx = context()
        self.assertEqual(diff.normalise_text("a  \r\nb\r\n\r\n", ctx), "a\nb")
        self.assertEqual(diff.normalise_text("hi [~amoreau] and [~ghost]", ctx), "hi [~accountid:5b10ac8d82e05b22cc7d4ef5] and [~ghost]")
        self.assertEqual(diff.normalise_text(None, ctx), "")


def m_ca1():
    return "5b10ac8d82e05b22cc7d4ef5"


def m_ca3():
    return "712020:6f1d2a3b-4c5d-4e6f-8a9b-0c1d2e3f4a5b"


if __name__ == "__main__":
    unittest.main()
