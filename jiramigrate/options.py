"""Option values of select-style custom fields, and what is missing on Cloud."""


def _flatten(allowed):
    """Option labels from allowedValues; children of a cascading select become 'Parent / Child'."""
    labels = []
    for option in allowed:
        label = option.get("value") or option.get("name")
        if label is None:
            continue
        labels.append(label)
        labels.extend("{} / {}".format(label, child.get("value") or child.get("name")) for child in option.get("children", []))
    return labels


def server_options(server):
    """{field id: {"name": ..., "values": [...]}} for every custom field with allowed values.

    Read from the create metadata of every project and issue type, so a field
    whose options differ per project gets the union.
    """
    data = server.get("issue/createmeta", {"expand": "projects.issuetypes.fields"})
    found = {}
    for project in data.get("projects", []):
        for issuetype in project.get("issuetypes", []):
            for field_id, field in issuetype.get("fields", {}).items():
                if field_id.startswith("customfield_") and field.get("allowedValues"):
                    entry = found.setdefault(field_id, {"name": field["name"], "values": set()})
                    entry["values"].update(_flatten(field["allowedValues"]))
    return {fid: {"name": e["name"], "values": sorted(e["values"], key=str.casefold)} for fid, e in sorted(found.items())}
