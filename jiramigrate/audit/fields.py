"""Custom field audit: duplicates, and fields nobody uses."""


def custom_fields(server):
    return [f for f in server.get("field") if f.get("custom")]


def field_type(field):
    schema = field.get("schema") or {}
    return schema.get("custom", "").rpartition(":")[2] or schema.get("type", "")


def duplicates(fields):
    """Groups of custom fields with the same name (ignoring case) and type.

    Cloud migrates every field it is given, so duplicates become duplicates in
    the new site too; merging them first is much cheaper than afterwards.
    """
    groups = {}
    for field in fields:
        key = (field["name"].strip().casefold(), (field.get("schema") or {}).get("custom", ""))
        groups.setdefault(key, []).append(field)
    return [members for members in groups.values() if len(members) > 1]


def duplicate_rows(fields):
    return [{"name": g[0]["name"], "type": field_type(g[0]), "ids": [f["id"] for f in g],
             "variants": sorted({f["name"] for f in g})} for g in duplicates(fields)]
