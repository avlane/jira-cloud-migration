"""User audit: accounts that will cause trouble when mapped to Cloud accounts by email."""
import re

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def all_users(server, page_size=1000):
    """Every user, including deactivated ones. `username=.` matches all names."""
    return list(server.paginate("user/search", params={"username": ".", "includeInactive": "true"}, page_size=page_size))


def audit(users):
    """One row per user with findings.

    no-email         Cloud matches people by email address, so there is nothing to match
    invalid-email    the address is not deliverable (no dot in the domain, for example)
    duplicate-email  another account uses the same address (compared ignoring case)
    inactive         deactivated; usually fine, but check they own nothing you still need
    """
    owners = {}
    for user in users:
        email = (user.get("emailAddress") or "").strip().casefold()
        if email:
            owners.setdefault(email, []).append(user["name"])
    rows = []
    for user in users:
        email = (user.get("emailAddress") or "").strip()
        found = []
        if not email:
            found.append("no-email")
        elif not _EMAIL.match(email):
            found.append("invalid-email")
        if email and len(owners.get(email.casefold(), [])) > 1:
            found.append("duplicate-email")
        if not user.get("active", True):
            found.append("inactive")
        rows.append({"key": user.get("key", ""), "name": user["name"], "displayName": user.get("displayName", ""),
                     "email": email, "active": user.get("active", True), "findings": found})
    return rows
