"""Permission and notification schemes that no project uses."""
from . import workflows


def permission_schemes(server):
    return server.get("permissionscheme")["permissionSchemes"]


def notification_schemes(server):
    return list(server.paginate("notificationscheme", page_size=50))


def _usage(server, kind):
    used = {}
    for project in workflows.projects(server):
        scheme = server.get("project/{}/{}".format(project["key"], kind))
        used.setdefault(scheme["id"], []).append(project["key"])
    return used


def report(server):
    rows = []
    for kind, label, listing in (("permissionscheme", "permission", permission_schemes), ("notificationscheme", "notification", notification_schemes)):
        used = _usage(server, kind)
        for scheme in listing(server):
            keys = used.get(scheme["id"], [])
            rows.append({"kind": label, "id": scheme["id"], "name": scheme["name"], "projects": keys, "finding": "" if keys else "unused"})
    return rows
