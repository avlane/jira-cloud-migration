"""Mapping Server users to Cloud accounts by email address."""


def lookup(cloud, email):
    """Cloud accounts whose attributes match the email (GET user/search?query=)."""
    return cloud.get("user/search", {"query": email, "maxResults": 20})


def map_user(cloud, server_user):
    """Row describing the Cloud account for one Server user."""
    email = (server_user.get("emailAddress") or "").strip()
    row = {"serverKey": server_user.get("key", ""), "serverName": server_user["name"], "email": email,
           "accountId": "", "cloudName": "", "status": "missing"}
    if not email:
        return row
    for account in lookup(cloud, email):
        if (account.get("emailAddress") or "").casefold() == email.casefold():
            row.update(accountId=account["accountId"], cloudName=account.get("displayName", ""), status="matched")
            break
    return row
