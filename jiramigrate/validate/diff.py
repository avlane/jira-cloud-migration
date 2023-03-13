"""Field-level comparison of one issue on both sites."""
from collections import namedtuple

Context = namedtuple("Context", "users names", defaults=({}, {}))


def _label(value):
    return (value or {}).get("name", "") if isinstance(value, dict) else (value or "")


def translate(ctx, kind, value):
    """The name the Cloud site should show for a Server name, using the (possibly hand-edited) names mapping."""
    return ctx.names.get(kind, {}).get(value, value)


def diff(subject, field, server_value, cloud_value, status="differs"):
    return {"check": "sample", "subject": subject, "field": field, "server": server_value, "cloud": cloud_value, "status": status}


SCALARS = (("summary", None), ("issuetype", "issuetype"), ("status", "status"), ("priority", "priority"), ("resolution", "resolution"))


def scalar_diffs(server_issue, cloud_issue, ctx):
    key = server_issue["key"]
    out = []
    for field, kind in SCALARS:
        theirs = _label(server_issue["fields"].get(field))
        expected = translate(ctx, kind, theirs) if kind else theirs.strip()
        actual = _label(cloud_issue["fields"].get(field))
        if (actual if kind else actual.strip()) != expected:
            out.append(diff(key, field, expected, actual))
    return out


def people_diffs(server_issue, cloud_issue, ctx):
    """Assignee and reporter, compared as Cloud account ids through the user mapping.

    A Server user with no entry in the mapping is reported as `unmapped-user` rather than as a
    difference: there is no account the issue could be expected to carry.
    """
    key = server_issue["key"]
    out = []
    for field in ("assignee", "reporter"):
        person = server_issue["fields"].get(field)
        actual = (cloud_issue["fields"].get(field) or {}).get("accountId", "")
        if not person:
            expected = ""
        elif person["name"] in ctx.users:
            expected = ctx.users[person["name"]]
        else:
            out.append(diff(key, field, person["name"], actual, status="unmapped-user"))
            continue
        if actual != expected:
            out.append(diff(key, field, expected or "(none)", actual or "(none)"))
    return out


SETS = (("labels", None), ("components", "name"), ("fixVersions", "name"))


def set_diffs(server_issue, cloud_issue):
    """Labels, components and fix versions as sets of names."""
    key = server_issue["key"]
    out = []
    for field, attribute in SETS:
        def names(issue):
            return {item[attribute] if attribute else item for item in issue["fields"].get(field) or []}
        theirs, ours = names(server_issue), names(cloud_issue)
        if theirs != ours:
            out.append(diff(key, field, ", ".join(sorted(theirs)), ", ".join(sorted(ours))))
    return out


def compare_issue(server_issue, cloud_issue, ctx):
    return scalar_diffs(server_issue, cloud_issue, ctx) + people_diffs(server_issue, cloud_issue, ctx) + set_diffs(server_issue, cloud_issue)
