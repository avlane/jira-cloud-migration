"""Issue counts per project, Server against Cloud."""
from ..api import ApiError

COLUMNS = ("check", "subject", "field", "server", "cloud", "status")

# (name, extra JQL, key in a snapshot file). Anything without a snapshot key is counted live on the Server.
METRICS = (
    ("issues", "", "issues"),
    ("withAttachments", "attachments is not EMPTY", "withAttachments"),
    ("resolved", "resolution is not EMPTY", None),
    ("assigned", "assignee is not EMPTY", None),
)


def project_jql(key, extra=""):
    return 'project = "{}"'.format(key) + (" AND " + extra if extra else "")


def cloud_count(cloud, jql):
    """Issue count on Cloud, or None when the query is rejected (a project that does not exist)."""
    try:
        return cloud.count(jql)
    except ApiError as exc:
        if exc.status == 400:
            return None
        raise


def row(subject, field, server_n, cloud_n):
    if cloud_n is None:
        status = "no-project"
    elif cloud_n == server_n:
        status = "ok"
    else:
        status = "cloud-has-fewer" if cloud_n < server_n else "cloud-has-more"
    return {"check": "count", "subject": subject, "field": field, "server": server_n, "cloud": cloud_n, "status": status}


def compare(server, cloud, projects=None, snapshot=None, metrics=METRICS):
    """Counts for each project and metric. With a snapshot the Server numbers are the recorded ones where it has them."""
    if projects:
        keys = list(projects)
    elif snapshot:
        keys = sorted(snapshot["projects"])
    else:
        keys = sorted(p["key"] for p in server.get("project"))
    rows = []
    for key in keys:
        recorded = (snapshot or {}).get("projects", {}).get(key, {})
        for name, extra, snapshot_key in metrics:
            expected = recorded[snapshot_key] if snapshot_key in recorded else server.count(project_jql(key, extra))
            rows.append(row(key, name, expected, cloud_count(cloud, project_jql(key, extra))))
    return rows
