"""Field-level comparison of one issue on both sites."""
import difflib
import re
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


_MENTION = re.compile(r"\[~([^\]:]+)\]")


def normalise_text(text, ctx):
    """Make Server and Cloud text comparable.

    Line endings and trailing blanks are not content. Server mentions, [~username], come back from
    Cloud as [~accountid:ID], so they are rewritten through the user mapping first.
    """
    text = (text or "").replace("\r\n", "\n").replace("\r", "\n")

    def mention(found):
        account = ctx.users.get(found.group(1))
        return "[~accountid:{}]".format(account) if account else found.group(0)

    text = _MENTION.sub(mention, text)
    return "\n".join(line.rstrip() for line in text.split("\n")).strip()


def _excerpt(text, width=60):
    text = " ".join(text.split())
    return text if len(text) <= width else text[:width - 3] + "..."


def text_diffs(server_issue, cloud_issue, ctx):
    """Description and comment bodies. Comments are compared pairwise; a different number of
    comments is reported by the count check instead."""
    key = server_issue["key"]
    pairs = [("description", server_issue["fields"].get("description"), cloud_issue["fields"].get("description"))]
    theirs = (server_issue["fields"].get("comment") or {}).get("comments", [])
    ours = (cloud_issue["fields"].get("comment") or {}).get("comments", [])
    for number, (a, b) in enumerate(zip(theirs, ours), 1):
        pairs.append(("comment {}".format(number), a.get("body"), b.get("body")))
    out = []
    for field, a, b in pairs:
        expected, actual = normalise_text(a, ctx), normalise_text(b, ctx)
        if expected != actual:
            ratio = difflib.SequenceMatcher(None, expected, actual).ratio()
            found = diff(key, field, _excerpt(expected), _excerpt(actual))
            found["note"] = "similarity {:.2f}".format(ratio)
            out.append(found)
    return out


def count_diffs(server_issue, cloud_issue):
    """Number of comments and attachments, and the total size of the attachments."""
    key = server_issue["key"]
    s, c = server_issue["fields"], cloud_issue["fields"]
    comments = ("comments", (s.get("comment") or {}).get("total", 0), (c.get("comment") or {}).get("total", 0))
    files = ("attachments", len(s.get("attachment") or []), len(c.get("attachment") or []))
    size = ("attachment bytes", sum(a.get("size", 0) for a in s.get("attachment") or []), sum(a.get("size", 0) for a in c.get("attachment") or []))
    return [diff(key, name, a, b) for name, a, b in (comments, files, size) if a != b]


def link_signatures(issue):
    """{'blocks PLAT-3', 'is blocked by PLAT-1', ...} read from issuelinks."""
    found = set()
    for entry in issue["fields"].get("issuelinks") or []:
        kind = entry.get("type") or {}
        if "outwardIssue" in entry:
            found.add("{} {}".format(kind.get("outward", kind.get("name", "")), entry["outwardIssue"]["key"]))
        elif "inwardIssue" in entry:
            found.add("{} {}".format(kind.get("inward", kind.get("name", "")), entry["inwardIssue"]["key"]))
    return found


def link_diffs(server_issue, cloud_issue):
    """Links that exist on only one side. Each link is one row, so a lost link is easy to find."""
    key = server_issue["key"]
    theirs, ours = link_signatures(server_issue), link_signatures(cloud_issue)
    return ([diff(key, "link", signature, "(missing)", "missing-link") for signature in sorted(theirs - ours)]
            + [diff(key, "link", "(none)", signature, "extra-link") for signature in sorted(ours - theirs)])


def compare_issue(server_issue, cloud_issue, ctx):
    return (link_diffs(server_issue, cloud_issue) + count_diffs(server_issue, cloud_issue) + scalar_diffs(server_issue, cloud_issue, ctx) + people_diffs(server_issue, cloud_issue, ctx)
            + set_diffs(server_issue, cloud_issue) + text_diffs(server_issue, cloud_issue, ctx))
