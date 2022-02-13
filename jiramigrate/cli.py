"""Command line entry point: jira-migrate <command>"""
import argparse
import sys

from . import config, report
from .api import Api, ApiError
from .audit import addons as audit_addons
from .audit import attachments as audit_attachments
from .audit import fields as audit_fields
from .audit import users as audit_users

FORMATS = ("table", "csv", "json")


def build_parser():
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--format", choices=FORMATS, default="table", help="output format (default table)")
    parser = argparse.ArgumentParser(prog="jira-migrate", description="Server/DC to Cloud migration helpers (read-only).")
    top = parser.add_subparsers(dest="command", required=True)
    audit = top.add_parser("audit", help="checks to run on the Server/DC site").add_subparsers(dest="what", required=True)
    p_fields = audit.add_parser("fields", parents=[common], help="custom fields: duplicates and unused")
    p_fields.add_argument("--unused", action="store_true", help="count issues per field and list the empty ones (slow)")
    audit.add_parser("users", parents=[common], help="users without a usable email address")
    audit.add_parser("addons", parents=[common], help="user-installed apps")
    p_att = audit.add_parser("attachments", parents=[common], help="attachments larger than a size limit")
    p_att.add_argument("--limit-mb", type=float, default=audit_attachments.DEFAULT_LIMIT_MB, help="size limit in MB (default 10)")
    p_att.add_argument("--totals", action="store_true", help="show total attachment size per project instead")
    return parser


def make_server():
    settings = config.server_from_env()
    auth = (settings.user, settings.password) if settings.user else None
    return Api(settings.url, auth=auth, token=settings.token)


def emit(rows, columns, args, out):
    out.write(report.render(rows, columns, args.format))
    return 0


def audit_fields_command(server, args, out):
    found = audit_fields.custom_fields(server)
    if args.unused:
        rows = audit_fields.unused(audit_fields.usage(server, found))
        return emit(rows, ("id", "name", "type", "issues"), args, out)
    return emit(audit_fields.duplicate_rows(found), ("name", "type", "ids", "variants"), args, out)


def audit_users_command(server, args, out):
    rows = [r for r in audit_users.audit(audit_users.all_users(server)) if r["findings"]]
    return emit(rows, ("key", "name", "displayName", "email", "active", "findings"), args, out)


def audit_attachments_command(server, args, out):
    if args.totals:
        return emit(audit_attachments.totals_by_project(server), ("project", "files", "sizeMB"), args, out)
    rows = audit_attachments.oversized(server, args.limit_mb)
    return emit(rows, ("project", "issue", "filename", "sizeMB", "mimeType", "author"), args, out)


def audit_addons_command(server, args, out):
    return emit(audit_addons.inventory(server), ("key", "name", "version", "vendor", "enabled", "licensed"), args, out)


def main(argv=None, server=None, out=None):
    out = out if out is not None else sys.stdout
    args = build_parser().parse_args(argv)
    try:
        server = server or make_server()
        if args.command == "audit" and args.what == "fields":
            return audit_fields_command(server, args, out)
        if args.command == "audit" and args.what == "users":
            return audit_users_command(server, args, out)
        if args.command == "audit" and args.what == "addons":
            return audit_addons_command(server, args, out)
        if args.command == "audit" and args.what == "attachments":
            return audit_attachments_command(server, args, out)
    except (config.ConfigError, ApiError) as exc:
        print("error: {}".format(exc), file=sys.stderr)
        return 2
    return 0
