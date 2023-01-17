"""Issue counts per project, Server against Cloud."""
from ..api import ApiError

COLUMNS = ("check", "subject", "field", "server", "cloud", "status")


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


def compare(server, cloud, projects=None, snapshot=None):
    """Issue counts for each project. With a snapshot the Server numbers are the recorded ones."""
    if projects:
        keys = list(projects)
    elif snapshot:
        keys = sorted(snapshot["projects"])
    else:
        keys = sorted(p["key"] for p in server.get("project"))
    rows = []
    for key in keys:
        recorded = (snapshot or {}).get("projects", {}).get(key)
        expected = recorded["issues"] if recorded else server.count(project_jql(key))
        rows.append(row(key, "issues", expected, cloud_count(cloud, project_jql(key))))
    return rows
