"""Connection settings from environment variables."""
import os
from collections import namedtuple

Server = namedtuple("Server", "url user password token")
Cloud = namedtuple("Cloud", "url email token")


class ConfigError(Exception):
    pass


def _https(name, value):
    value = value.strip().rstrip("/")
    if not value.startswith(("https://", "http://")):
        raise ConfigError("{} must start with https:// (got {!r})".format(name, value))
    return value


def server_from_env(environ=None):
    """Server/DC settings: a URL plus either a personal access token or a user and password."""
    env = os.environ if environ is None else environ
    if not env.get("JIRA_SERVER_URL"):
        raise ConfigError("missing environment variable: JIRA_SERVER_URL")
    token = env.get("JIRA_SERVER_TOKEN") or None
    user, password = env.get("JIRA_SERVER_USER") or None, env.get("JIRA_SERVER_PASSWORD") or None
    if not token and not (user and password):
        raise ConfigError("set JIRA_SERVER_TOKEN, or both JIRA_SERVER_USER and JIRA_SERVER_PASSWORD")
    return Server(_https("JIRA_SERVER_URL", env["JIRA_SERVER_URL"]), user, password, token)


def cloud_from_env(environ=None):
    env = os.environ if environ is None else environ
    names = ("JIRA_CLOUD_URL", "JIRA_CLOUD_EMAIL", "JIRA_CLOUD_API_TOKEN")
    missing = [n for n in names if not env.get(n)]
    if missing:
        raise ConfigError("missing environment variable(s): " + ", ".join(missing))
    url = _https("JIRA_CLOUD_URL", env["JIRA_CLOUD_URL"])
    if not url.startswith("https://"):
        raise ConfigError("JIRA_CLOUD_URL must use https://")
    return Cloud(url, env["JIRA_CLOUD_EMAIL"].strip(), env["JIRA_CLOUD_API_TOKEN"].strip())
