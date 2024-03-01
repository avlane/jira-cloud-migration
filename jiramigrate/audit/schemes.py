"""Permission and notification schemes that no project uses."""
from ..api import ApiError
from . import workflows


def permission_schemes(server):
    return server.get("permissionscheme")["permissionSchemes"]


def notification_schemes(server):
    return list(server.paginate("notificationscheme", page_size=50))


def _usage(server, kind, skipped):
    used = {}
    for project in workflows.projects(server):
        try:
            scheme = server.get("project/{}/{}".format(project["key"], kind))
        except ApiError as exc:
            if exc.status not in (403, 404):
                raise
            if project["key"] not in skipped:
                skipped.append(project["key"])
            continue
        used.setdefault(scheme["id"], []).append(project["key"])
    return used


def report(server):
    rows, skipped = [], []
    for kind, label, listing in (("permissionscheme", "permission", permission_schemes), ("notificationscheme", "notification", notification_schemes)):
        used = _usage(server, kind, skipped)
        for scheme in listing(server):
            keys = used.get(scheme["id"], [])
            rows.append({"kind": label, "id": scheme["id"], "name": scheme["name"], "projects": keys,
                         "finding": "" if keys else ("maybe-unused" if skipped else "unused")})
    for key in skipped:
        rows.append({"kind": "project", "id": "", "name": key, "projects": [key], "finding": "project-unreadable"})
    return rows
