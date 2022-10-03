"""Mapping files: what the map commands write and later steps read."""
import json
from datetime import datetime, timezone

VERSION = 1
KINDS = ("users", "fields", "names", "options")


def build(kind, rows, server_url, cloud_url, summary=None, now=None):
    if kind not in KINDS:
        raise ValueError("unknown mapping kind {!r}".format(kind))
    now = now or datetime.now(timezone.utc)
    return {"version": VERSION, "kind": kind, "generated": now.isoformat(timespec="seconds"), "server": server_url,
            "cloud": cloud_url, "summary": summary if summary is not None else status_counts(rows), "items": rows}


def status_counts(rows):
    counts = {}
    for row in rows:
        counts[row.get("status", "")] = counts.get(row.get("status", ""), 0) + 1
    return counts


def write(path, data):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def read(path, kind=None):
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    if data.get("version") != VERSION:
        raise ValueError("{} is mapping file version {!r}, expected {}".format(path, data.get("version"), VERSION))
    if kind and data.get("kind") != kind:
        raise ValueError("{} is a {} mapping, not {}".format(path, data.get("kind"), kind))
    return data
