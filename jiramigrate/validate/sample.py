"""Reproducible samples of issues, fetched from both sites."""
import random

FIELDS = ("summary", "issuetype", "status", "priority", "resolution", "assignee", "reporter", "labels", "components",
          "fixVersions", "description", "comment", "attachment", "issuelinks")


def key_number(key):
    return int(key.rsplit("-", 1)[1])


def chunks(items, size):
    for start in range(0, len(items), size):
        yield items[start:start + size]


def newest_number(server, project):
    for issue in server.search('project = "{}" ORDER BY key DESC'.format(project), fields=("key",), page_size=1):
        return key_number(issue["key"])
    return 0


def pick_keys(server, project, n, seed):
    """Up to n existing issue keys of a project, the same ones every time for the same seed.

    Random issue numbers are drawn up to the newest key; some of them no longer exist (deleted or moved
    issues), so twice as many are drawn as needed and checked with one `key in (...)` query.
    """
    top = newest_number(server, project)
    if top == 0:
        return []
    rng = random.Random("{}:{}".format(seed, project))
    keys = ["{}-{}".format(project, number) for number in rng.sample(range(1, top + 1), min(top, n * 2))]
    existing = set()
    for batch in chunks(keys, 100):
        for issue in server.search("key in ({})".format(", ".join(batch)), fields=("key",), page_size=100):
            existing.add(issue["key"])
    return sorted([k for k in keys if k in existing][:n], key=key_number)


def fetch_issues(api, keys, fields=FIELDS, cache=None):
    """{key: issue} for the keys that exist on that site.

    With a cache, issues fetched on an earlier run are reused. Only do that for a site that is not
    changing (the Server, once it is frozen for the final migration): cached copies are never refreshed.
    """
    found, missing = {}, []
    for key in keys:
        cached = cache.get("issue-" + key) if cache else None
        if cached and cached.get("fields") == list(fields):
            found[key] = cached["issue"]
        else:
            missing.append(key)
    for batch in chunks(missing, 50):
        for issue in api.search("key in ({})".format(", ".join(batch)), fields=fields, page_size=50):
            found[issue["key"]] = issue
            if cache:
                cache.set("issue-" + issue["key"], {"fields": list(fields), "issue": issue})
    return found
