"""Reproducible samples of issues, fetched from both sites."""
import random

FIELDS = ("summary", "issuetype", "status", "priority", "resolution", "assignee", "reporter", "labels", "components",
          "fixVersions", "description", "comment", "attachment", "issuelinks", "timespent", "timeoriginalestimate")


def key_number(key):
    return int(key.rsplit("-", 1)[1])


def chunks(items, size):
    for start in range(0, len(items), size):
        yield items[start:start + size]


def newest_number(server, project):
    for issue in server.search('project = "{}" ORDER BY key DESC'.format(project), fields=("key",), page_size=1):
        return key_number(issue["key"])
    return 0


def edge_keys(server, project):
    """The oldest and the newest issue of a project by creation time.

    Imports tend to go wrong at the ends: the first issue exercises old field values and schemes,
    the last one shows whether the final delta made it across.
    """
    found = []
    for order in ("ASC", "DESC"):
        for issue in server.search('project = "{}" ORDER BY created {}'.format(project, order), fields=("key",), page_size=1):
            found.append(issue["key"])
            break
    return list(dict.fromkeys(found))


def pick_keys(server, project, n, seed, edges=True):
    """Up to n existing issue keys of a project, the same ones every time for the same seed.

    The oldest and newest issues come first (unless edges is False); the rest are random. Random issue
    numbers are drawn up to the newest key; some of them no longer exist (deleted or moved issues), so
    twice as many are drawn as needed and checked with one `key in (...)` query.
    """
    top = newest_number(server, project)
    if top == 0:
        return []
    fixed = edge_keys(server, project)[:n] if edges else []
    rng = random.Random("{}:{}".format(seed, project))
    keys = ["{}-{}".format(project, number) for number in rng.sample(range(1, top + 1), min(top, n * 2))]
    existing = set()
    for batch in chunks(keys, 100):
        for issue in server.search("key in ({})".format(", ".join(batch)), fields=("key",), page_size=100):
            existing.add(issue["key"])
    chosen = list(dict.fromkeys(fixed + [k for k in keys if k in existing]))[:n]
    return sorted(chosen, key=key_number)


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
