"""Apps installed on the Server/DC site (from the Universal Plugin Manager)."""


def installed_apps(server):
    """User-installed apps, via GET /rest/plugins/1.0/ (needs a system administrator)."""
    data = server.get("/rest/plugins/1.0/")
    return [p for p in data.get("plugins", []) if p.get("userInstalled")]


def inventory(server):
    rows = []
    for plugin in installed_apps(server):
        rows.append({"key": plugin["key"], "name": plugin["name"], "version": plugin.get("version", ""),
                     "vendor": (plugin.get("vendor") or {}).get("name", ""), "enabled": plugin.get("enabled", False),
                     "licensed": plugin.get("usesLicensing", False)})
    return sorted(rows, key=lambda r: r["name"].casefold())
