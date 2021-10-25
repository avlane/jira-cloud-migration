import unittest

from jiramigrate import config

SERVER_PASSWORD = {"JIRA_SERVER_URL": "https://jira.corp.example.com/", "JIRA_SERVER_USER": "svc", "JIRA_SERVER_PASSWORD": "pw"}
CLOUD = {"JIRA_CLOUD_URL": "https://example.atlassian.net/", "JIRA_CLOUD_EMAIL": " ops@example.com ", "JIRA_CLOUD_API_TOKEN": "tok"}


class ServerConfigTests(unittest.TestCase):
    def test_user_and_password(self):
        got = config.server_from_env(SERVER_PASSWORD)
        self.assertEqual(got, ("https://jira.corp.example.com", "svc", "pw", None))

    def test_token(self):
        got = config.server_from_env({"JIRA_SERVER_URL": "https://jira.corp.example.com", "JIRA_SERVER_TOKEN": "pat"})
        self.assertEqual((got.token, got.user), ("pat", None))

    def test_needs_some_credentials(self):
        with self.assertRaises(config.ConfigError):
            config.server_from_env({"JIRA_SERVER_URL": "https://jira.corp.example.com", "JIRA_SERVER_USER": "svc"})
        with self.assertRaises(config.ConfigError):
            config.server_from_env({})

    def test_plain_http_is_allowed_for_server_only(self):
        got = config.server_from_env(dict(SERVER_PASSWORD, JIRA_SERVER_URL="http://jira.corp.example.com:8080"))
        self.assertEqual(got.url, "http://jira.corp.example.com:8080")
        with self.assertRaises(config.ConfigError):
            config.cloud_from_env(dict(CLOUD, JIRA_CLOUD_URL="http://example.atlassian.net"))


class CloudConfigTests(unittest.TestCase):
    def test_reads_and_normalises(self):
        self.assertEqual(config.cloud_from_env(CLOUD), ("https://example.atlassian.net", "ops@example.com", "tok"))

    def test_names_what_is_missing(self):
        with self.assertRaises(config.ConfigError) as ctx:
            config.cloud_from_env({"JIRA_CLOUD_URL": "https://example.atlassian.net"})
        self.assertIn("JIRA_CLOUD_EMAIL", str(ctx.exception))
        self.assertIn("JIRA_CLOUD_API_TOKEN", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
