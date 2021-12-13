"""Attachment audit: files larger than the limit you plan to allow on Cloud."""

DEFAULT_LIMIT_MB = 10


def iter_attachments(server):
    """Yield (project key, issue key, attachment) for every attachment on the site."""
    for issue in server.search("attachments is not EMPTY", fields=("attachment", "project"), page_size=100):
        project = issue["fields"]["project"]["key"]
        for attachment in issue["fields"].get("attachment") or []:
            yield project, issue["key"], attachment


def oversized(server, limit_mb=DEFAULT_LIMIT_MB):
    """Attachments strictly larger than limit_mb megabytes (1 MB = 1048576 bytes), biggest first."""
    limit = int(limit_mb * 1024 * 1024)
    rows = [{"project": project, "issue": key, "id": a["id"], "filename": a["filename"], "size": a["size"],
             "sizeMB": round(a["size"] / 1048576, 1), "mimeType": a.get("mimeType", ""),
             "author": (a.get("author") or {}).get("name", "")}
            for project, key, a in iter_attachments(server) if a["size"] > limit]
    return sorted(rows, key=lambda r: -r["size"])


def totals_by_project(server):
    totals = {}
    for project, _key, attachment in iter_attachments(server):
        entry = totals.setdefault(project, {"project": project, "files": 0, "bytes": 0})
        entry["files"] += 1
        entry["bytes"] += attachment["size"]
    return [dict(t, sizeMB=round(t["bytes"] / 1048576, 1)) for t in sorted(totals.values(), key=lambda t: -t["bytes"])]
