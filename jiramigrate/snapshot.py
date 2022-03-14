"""A baseline of the Server site to compare the Cloud site with after the migration."""
import json
from datetime import datetime, timezone

VERSION = 1


def take(server, now=None):
    """Per-project issue counts and the time of the newest update, taken just before the final migration run."""
    from .audit import workflows

    now = now or datetime.now(timezone.utc)
    projects = {}
    for project in workflows.projects(server):
        key = project["key"]
        newest = None
        for issue in server.search('project = "{}" ORDER BY updated DESC'.format(key), fields=("updated",), page_size=1):
            newest = issue["fields"]["updated"]
            break
        projects[key] = {
            "name": project["name"],
            "issues": server.count('project = "{}"'.format(key)),
            "withAttachments": server.count('project = "{}" AND attachments is not EMPTY'.format(key)),
            "lastUpdated": newest,
        }
    return {"version": VERSION, "taken": now.isoformat(timespec="seconds"), "server": server.base_url, "projects": projects}


def save(path, snapshot):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(snapshot, handle, indent=2, sort_keys=True)
        handle.write("\n")


def load(path):
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    if data.get("version") != VERSION:
        raise ValueError("{} is snapshot version {!r}, expected {}".format(path, data.get("version"), VERSION))
    return data
