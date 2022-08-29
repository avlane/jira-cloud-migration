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


def cloud_options(cloud, field_id):
    """Option labels of a Cloud field, unioned over all its contexts. A child option is 'Parent / Child'."""
    labels = set()
    for context in cloud.paginate("field/{}/context".format(field_id), page_size=50):
        entries = list(cloud.paginate("field/{}/context/{}/option".format(field_id, context["id"]), page_size=100))
        parents = {e["id"]: e["value"] for e in entries if "optionId" not in e}
        for entry in entries:
            if "optionId" in entry:
                labels.add("{} / {}".format(parents.get(entry["optionId"], "?"), entry["value"]))
            else:
                labels.add(entry["value"])
    return sorted(labels, key=str.casefold)


COLUMNS = ("serverId", "name", "cloudId", "missingOnCloud", "extraOnCloud", "status")


def compare(cloud, server_opts, field_rows):
    """For each matched select field, which Server options Cloud lacks (and which only Cloud has)."""
    cloud_ids = {r["serverId"]: r["cloudId"] for r in field_rows if r["status"] == "matched"}
    rows = []
    for field_id, entry in server_opts.items():
        cloud_id = cloud_ids.get(field_id)
        if not cloud_id:
            rows.append({"serverId": field_id, "name": entry["name"], "cloudId": "", "missingOnCloud": [], "extraOnCloud": [], "status": "no-cloud-field"})
            continue
        theirs = cloud_options(cloud, cloud_id)
        have = {v.casefold() for v in theirs}
        wanted = {v.casefold() for v in entry["values"]}
        missing = [v for v in entry["values"] if v.casefold() not in have]
        extra = [v for v in theirs if v.casefold() not in wanted]
        rows.append({"serverId": field_id, "name": entry["name"], "cloudId": cloud_id, "missingOnCloud": missing, "extraOnCloud": extra,
                     "status": "differs" if missing else "complete"})
    return rows
