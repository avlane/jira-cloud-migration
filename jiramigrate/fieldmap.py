"""Mapping Server custom fields to their Cloud equivalents."""
from .audit.fields import field_type

COLUMNS = ("serverId", "name", "type", "cloudId", "status", "note")


def cloud_custom_fields(cloud):
    return [f for f in cloud.get("field") if f.get("custom")]


def _signature(field):
    return field["name"].strip().casefold(), (field.get("schema") or {}).get("custom", "")


def map_fields(server_fields, cloud_fields):
    """One row per Server custom field.

    matched        a Cloud field with the same name and field type
    type-mismatch  a Cloud field with the same name but another type, so values would not carry over
    missing        nothing with that name on Cloud
    """
    by_signature, by_name = {}, {}
    for field in cloud_fields:
        by_signature.setdefault(_signature(field), field)
        by_name.setdefault(field["name"].strip().casefold(), field)
    rows = []
    for field in server_fields:
        row = {"serverId": field["id"], "name": field["name"], "type": field_type(field), "cloudId": "", "status": "missing", "note": ""}
        exact = by_signature.get(_signature(field))
        same_name = by_name.get(field["name"].strip().casefold())
        if exact:
            row.update(cloudId=exact["id"], status="matched")
        elif same_name:
            row.update(cloudId=same_name["id"], status="type-mismatch",
                       note="Cloud field is a {}".format(field_type(same_name)))
        rows.append(row)
    return rows
