"""Statuses, issue types, priorities and resolutions: which Server names exist on Cloud."""

COLUMNS = ("kind", "serverName", "serverId", "cloudName", "cloudId", "status")
KINDS = ("status", "issuetype", "priority", "resolution")


def map_kind(kind, server_items, cloud_items):
    by_name = {item["name"].strip().casefold(): item for item in cloud_items}
    rows = []
    for item in server_items:
        other = by_name.get(item["name"].strip().casefold())
        rows.append({"kind": kind, "serverName": item["name"], "serverId": item["id"],
                     "cloudName": other["name"] if other else "", "cloudId": other["id"] if other else "",
                     "status": "matched" if other else "missing"})
    return rows


def map_names(server, cloud, kinds=KINDS):
    """Compare each list endpoint on both sites. Names are matched ignoring case."""
    rows = []
    for kind in kinds:
        rows.extend(map_kind(kind, server.get(kind), cloud.get(kind)))
    return rows
