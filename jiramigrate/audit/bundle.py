"""Run every audit and keep the results together."""
from . import addons, attachments, fields, schemes, users, workflows

NAMES = ("fields", "users", "workflows", "schemes", "attachments", "addons")


def run_all(server, cloud_apps=None, limit_mb=attachments.DEFAULT_LIMIT_MB):
    """{audit name: rows that need attention}. Rows without a finding are left out."""
    found = fields.custom_fields(server)
    return {
        "fields": fields.duplicate_rows(found),
        "users": [r for r in users.audit(users.all_users(server)) if r["findings"]],
        "workflows": [r for r in workflows.report(server) if r["finding"]],
        "schemes": [r for r in schemes.report(server) if r["finding"]],
        "attachments": attachments.oversized(server, limit_mb),
        "addons": [r for r in addons.inventory(server, cloud_apps) if r["finding"]],
    }


def headline(results):
    return [{"audit": name, "rows": len(results[name])} for name in NAMES]
