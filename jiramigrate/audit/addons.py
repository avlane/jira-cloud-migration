"""Apps installed on the Server/DC site (from the Universal Plugin Manager)."""


def installed_apps(server):
    """User-installed apps, via GET /rest/plugins/1.0/ (needs a system administrator)."""
    data = server.get("/rest/plugins/1.0/")
    return [p for p in data.get("plugins", []) if p.get("userInstalled")]


def verdict(plugin, cloud_apps):
    """What to do about one app, given a {key: {"cloud": "available" | "none", "note": ...}} file you maintain.

    disabled         switched off on Server; probably not worth migrating
    no-cloud-version the vendor has no Cloud edition; decide on a replacement or going without
    unknown          not in your list yet; look it up on the Marketplace
    """
    if not plugin.get("enabled", False):
        return "disabled", ""
    entry = (cloud_apps or {}).get(plugin["key"])
    if cloud_apps is None:
        return "", ""
    if entry is None:
        return "unknown", ""
    if entry.get("cloud") == "none":
        return "no-cloud-version", entry.get("note", "")
    return "", entry.get("note", "")


def inventory(server, cloud_apps=None):
    rows = []
    for plugin in installed_apps(server):
        finding, note = verdict(plugin, cloud_apps)
        rows.append({"key": plugin["key"], "name": plugin["name"], "version": plugin.get("version", ""),
                     "vendor": (plugin.get("vendor") or {}).get("name", ""), "enabled": plugin.get("enabled", False),
                     "licensed": plugin.get("usesLicensing", False), "finding": finding, "note": note})
    return sorted(rows, key=lambda r: r["name"].casefold())
