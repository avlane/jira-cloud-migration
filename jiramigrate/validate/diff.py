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


def compare_issue(server_issue, cloud_issue, ctx):
    return scalar_diffs(server_issue, cloud_issue, ctx)
