import unittest

from jiramigrate.api import Api, ApiError
from tests.helpers import FakeResponse, FakeSession, Seq, counts_handler, load, paged, search_handler


def make(session, **kwargs):
    return Api("https://jira.corp.example.com/", session=session, sleep=lambda s: None, **kwargs)


class RequestTests(unittest.TestCase):
    def test_url_building(self):
        api = make(FakeSession())
        self.assertEqual(api.url("field"), "https://jira.corp.example.com/rest/api/2/field")
        self.assertEqual(api.url("/rest/plugins/1.0/"), "https://jira.corp.example.com/rest/plugins/1.0/")
        cloud = Api("https://example.atlassian.net", prefix="/rest/api/3/", session=FakeSession())
        self.assertEqual(cloud.url("field"), "https://example.atlassian.net/rest/api/3/field")

    def test_basic_auth_is_passed_per_request(self):
        seen = {}

        class Recording(FakeSession):
            def request(self, method, url, **kwargs):
                seen.update(kwargs)
                return super().request(method, url, **kwargs)

        session = Recording().add("GET", r"/field$", [])
        make(session, auth=("svc", "pw")).get("field")
        self.assertEqual(seen["auth"], ("svc", "pw"))
        self.assertNotIn("Authorization", seen["headers"])

    def test_bearer_token(self):
        seen = {}

        class Recording(FakeSession):
            def request(self, method, url, **kwargs):
                seen.update(kwargs)
                return super().request(method, url, **kwargs)

        make(Recording().add("GET", r"/field$", []), token="pat123").get("field")
        self.assertEqual(seen["headers"]["Authorization"], "Bearer pat123")
        self.assertNotIn("auth", seen)

    def test_errors_carry_the_status(self):
        session = FakeSession().add("GET", r"/field$", FakeResponse(401, {"message": "no"}))
        with self.assertRaises(ApiError) as ctx:
            make(session).get("field")
        self.assertEqual(ctx.exception.status, 401)

    def test_auth_and_permission_errors_explain_themselves(self):
        for status, hint in ((401, "credentials"), (403, "Administer Jira"), (404, "does not exist on that Jira version")):
            session = FakeSession().add("GET", r"/field$", FakeResponse(status, {"message": "no"}))
            with self.assertRaises(ApiError) as ctx:
                make(session).get("field")
            self.assertIn(hint, str(ctx.exception))

    def test_other_errors_have_no_hint(self):
        session = FakeSession().add("GET", r"/field$", FakeResponse(400, {"message": "bad"}))
        with self.assertRaises(ApiError) as ctx:
            make(session).get("field")
        self.assertNotIn("(check", str(ctx.exception))

    def test_429_is_retried(self):
        limited = FakeResponse(429, None, {"Retry-After": "4"})
        session = FakeSession().add("GET", r"/field$", Seq(limited, {"ok": 1}))
        sleeps = []
        api = Api("https://jira.corp.example.com", session=session, sleep=sleeps.append)
        self.assertEqual(api.get("field"), {"ok": 1})
        self.assertEqual(sleeps, [4])


class TransientErrorTests(unittest.TestCase):
    def test_gateway_errors_on_reads_are_retried_with_backoff(self):
        session = FakeSession().add("GET", r"/field$", Seq(FakeResponse(503), FakeResponse(502), {"ok": 1}))
        sleeps = []
        api = Api("https://jira.corp.example.com", session=session, sleep=sleeps.append)
        self.assertEqual(api.get("field"), {"ok": 1})
        self.assertEqual(sleeps, [2, 4])

    def test_gives_up_eventually(self):
        session = FakeSession().add("GET", r"/field$", FakeResponse(504, "gateway timeout"))
        api = Api("https://jira.corp.example.com", session=session, sleep=lambda s: None, max_retries=2)
        with self.assertRaises(ApiError) as ctx:
            api.get("field")
        self.assertEqual(ctx.exception.status, 504)
        self.assertEqual(len(session.calls), 3)

    def test_writes_are_not_repeated(self):
        session = FakeSession().add("POST", r"/thing$", FakeResponse(503, "unavailable"))
        api = Api("https://jira.corp.example.com", session=session, sleep=lambda s: None)
        with self.assertRaises(ApiError):
            api.request("POST", "thing", body={})
        self.assertEqual(len(session.calls), 1)

    def test_waits_are_logged(self):
        session = FakeSession().add("GET", r"/field$", Seq(FakeResponse(429, None, {"Retry-After": "3"}), {"ok": 1}))
        api = Api("https://jira.corp.example.com", session=session, sleep=lambda s: None)
        with self.assertLogs("jiramigrate.api", level="WARNING") as captured:
            api.get("field")
        self.assertIn("waiting 3s (retry 1 of 5)", captured.output[0])


class PagingTests(unittest.TestCase):
    def test_bare_arrays_and_paged_objects(self):
        items = [{"n": n} for n in range(7)]
        session = FakeSession().add("GET", r"/a$", paged(items, cap=3)).add("GET", r"/b$", paged(items, key="values", cap=3))
        api = make(session)
        self.assertEqual(len(list(api.paginate("a"))), 7)
        self.assertEqual(len(list(api.paginate("b"))), 7)

    def test_search_and_count(self):
        session = FakeSession().add("GET", r"/rest/api/2/search$", search_handler([{"key": "A-1"}, {"key": "A-2"}, {"key": "A-3"}]))
        api = make(session)
        self.assertEqual([i["key"] for i in api.search("project = A", fields=("summary",), page_size=2)], ["A-1", "A-2", "A-3"])
        self.assertEqual(session.calls[0]["params"]["fields"], "summary")
        self.assertEqual(api.count("project = A"), 3)
        self.assertEqual(session.calls[-1]["params"]["maxResults"], 0)

    def test_count_handler_helper(self):
        session = FakeSession().add("GET", r"/search$", counts_handler({"project = A": 12}))
        api = make(session)
        self.assertEqual(api.count("project = A AND x"), 12)
        self.assertEqual(api.count("project = B"), 0)


if __name__ == "__main__":
    unittest.main()
