"""Mapping Server users to Cloud accounts by email address."""

COLUMNS = ("serverKey", "serverName", "displayName", "email", "accountId", "cloudName", "status", "note")


def lookup(cloud, email):
    """Cloud accounts whose attributes match the email (GET user/search?query=)."""
    return cloud.get("user/search", {"query": email, "maxResults": 20})


def map_user(cloud, server_user):
    """Row describing the Cloud account for one Server user.

    matched    one Cloud account shows exactly this email address
    probable   the search found a single account but Cloud hides its email address (profile
               visibility), so it could not be confirmed; check before relying on it
    ambiguous  several candidates and none confirmed
    missing    nobody found; the person needs inviting, or uses another address on Cloud
    no-email   the Server account has no email address to search for
    """
    email = (server_user.get("emailAddress") or "").strip()
    row = {"serverKey": server_user.get("key", ""), "serverName": server_user["name"], "displayName": server_user.get("displayName", ""),
           "email": email, "accountId": "", "cloudName": "", "status": "missing", "note": ""}
    if not email:
        row["status"] = "no-email"
        return row
    people = [a for a in lookup(cloud, email) if a.get("accountType", "atlassian") == "atlassian"]
    exact = [a for a in people if (a.get("emailAddress") or "").casefold() == email.casefold()]
    hidden = [a for a in people if not a.get("emailAddress")]
    if len(exact) == 1:
        chosen, status = exact[0], "matched"
    elif len(exact) > 1:
        return dict(row, status="ambiguous", note="{} accounts show this email".format(len(exact)))
    elif len(hidden) == 1 and len(people) == 1:
        chosen, status = hidden[0], "probable"
        row["note"] = "email hidden on Cloud; confirm by name"
    elif people:
        return dict(row, status="ambiguous", note="{} candidates, none with a visible email".format(len(people)))
    else:
        return row
    row.update(accountId=chosen["accountId"], cloudName=chosen.get("displayName", ""), status=status)
    if not chosen.get("active", True):
        row["note"] = (row["note"] + "; " if row["note"] else "") + "Cloud account is deactivated"
    return row


def map_users(cloud, server_users):
    """Map every user; an email shared by several Server accounts goes to the first one only."""
    claimed = {}
    rows = []
    for user in server_users:
        row = map_user(cloud, user)
        email = row["email"].casefold()
        if row["status"] in ("matched", "probable"):
            if email in claimed:
                row.update(accountId="", cloudName="", status="duplicate", note="same email as {}".format(claimed[email]))
            else:
                claimed[email] = row["serverName"]
        rows.append(row)
    return rows


def summary(rows):
    """Counts by status, e.g. {"matched": 5, "missing": 1}."""
    counts = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    return counts


def mention_names(rows):
    """Server username -> accountId, for rewriting [~username] mentions in text after the import."""
    return {r["serverName"]: r["accountId"] for r in rows if r["accountId"]}
