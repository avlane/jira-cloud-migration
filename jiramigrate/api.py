"""A small REST client used for both the Server/DC side and the Cloud side."""
import logging
import time


log = logging.getLogger("jiramigrate.api")

# Gateway errors during short outages; only reads are repeated.
TRANSIENT = (502, 503, 504)


class ApiError(Exception):
    def __init__(self, message, status=None, url=None):
        super().__init__(message)
        self.status = status
        self.url = url


def default_session():
    import requests  # imported lazily so the tests run without it installed

    session = requests.Session()
    session.headers.update({"User-Agent": "jira-cloud-migration/0.1"})
    return session


def retry_after(resp, default=5):
    try:
        return max(0, int(resp.headers.get("Retry-After")))
    except (TypeError, ValueError):
        return default


class Api:
    """One Jira site. `auth` is a (user, secret) pair for basic auth, `token` a bearer token (Data Center PAT)."""

    def __init__(self, base_url, auth=None, token=None, session=None, prefix="/rest/api/2/", timeout=60,
                 max_retries=5, sleep=time.sleep):
        self.base_url = base_url.rstrip("/")
        self.auth = auth
        self.token = token
        self.session = session if session is not None else default_session()
        self.prefix = prefix
        self.timeout = timeout
        self.max_retries = max_retries
        self.sleep = sleep

    def url(self, path):
        if path.startswith("/rest/"):
            return self.base_url + path
        return self.base_url + self.prefix + path.lstrip("/")

    def request(self, method, path, params=None, body=None, expected=(200,)):
        url = self.url(path)
        headers = {"Accept": "application/json"}
        extra = {}
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        elif self.auth:
            extra["auth"] = self.auth
        attempt = 0
        while True:
            resp = self.session.request(method, url, params=params, json=body, headers=headers, timeout=self.timeout, **extra)
            if resp.status_code == 429 and attempt < self.max_retries:
                attempt += 1
                delay = retry_after(resp)
                log.warning("rate limited on %s; waiting %ss (retry %d of %d)", url, delay, attempt, self.max_retries)
                self.sleep(delay)
                continue
            if resp.status_code in TRANSIENT and method.upper() == "GET" and attempt < self.max_retries:
                attempt += 1
                delay = min(2 ** attempt, 30)
                log.warning("HTTP %s from %s; retrying in %ss (retry %d of %d)", resp.status_code, url, delay, attempt, self.max_retries)
                self.sleep(delay)
                continue
            break
        if resp.status_code not in expected:
            raise ApiError("{} {} failed with HTTP {}: {}".format(method, url, resp.status_code, resp.text[:200]), resp.status_code, url)
        if resp.status_code == 204 or not resp.text:
            return None
        return resp.json()

    def get(self, path, params=None):
        return self.request("GET", path, params=params)

    def paginate(self, path, params=None, key="values", page_size=50):
        """Yield every item of a startAt/maxResults endpoint (paged object or bare array)."""
        start = 0
        while True:
            query = dict(params or {})
            query.update({"startAt": start, "maxResults": page_size})
            data = self.get(path, query)
            items = data if isinstance(data, list) else data.get(key, [])
            for item in items:
                yield item
            if not items:
                return
            if isinstance(data, dict):
                if data.get("isLast") is True:
                    return
                total = data.get("total")
                if total is not None and start + len(items) >= total:
                    return
            start += len(items)

    def search(self, jql, fields=(), page_size=100):
        """Yield issues matching a JQL query (the classic startAt search that Server and DC provide)."""
        start = 0
        while True:
            params = {"jql": jql, "startAt": start, "maxResults": page_size}
            if fields:
                params["fields"] = ",".join(fields)
            data = self.get("search", params)
            batch = data["issues"]
            for issue in batch:
                yield issue
            start += len(batch)
            if not batch or start >= data["total"]:
                return

    def count(self, jql):
        """Number of issues matching a JQL query, without fetching them."""
        return self.get("search", {"jql": jql, "maxResults": 0, "fields": "key"})["total"]
