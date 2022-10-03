"""Command line entry point: jira-migrate <command>"""
import argparse
import json
import sys

from . import config, fieldmap, mapfile, namemap, options, report, snapshot, usermap
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
    p_addons = audit.add_parser("addons", parents=[common], help="user-installed apps")
    p_addons.add_argument("--cloud-apps", metavar="FILE", help="JSON file of {app key: {cloud: available|none, note}} to check against")
    p_att = audit.add_parser("attachments", parents=[common], help="attachments larger than a size limit")
    p_att.add_argument("--limit-mb", type=float, default=audit_attachments.DEFAULT_LIMIT_MB, help="size limit in MB (default 10)")
    p_att.add_argument("--totals", action="store_true", help="show total attachment size per project instead")
    p_snap = top.add_parser("snapshot", help="record per-project issue counts on the Server site")
    p_snap.add_argument("--output", "-o", required=True, help="where to write the snapshot JSON")
    mapping = top.add_parser("map", help="build mapping files between the Server and Cloud sites").add_subparsers(dest="what", required=True)
    for name, helptext in (("users", "Server users -> Cloud accounts, by email"), ("fields", "Server custom fields -> Cloud fields"),
                           ("names", "statuses, issue types, priorities, resolutions by name"), ("options", "select field options missing on Cloud")):
        p = mapping.add_parser(name, parents=[common], help=helptext)
        p.add_argument("--output", "-o", metavar="FILE", help="also write the mapping file (JSON) here")
    return parser


def make_cloud():
    settings = config.cloud_from_env()
    return Api(settings.url, auth=(settings.email, settings.token), prefix="/rest/api/3/")


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
    cloud_apps = None
    if args.cloud_apps:
        with open(args.cloud_apps, encoding="utf-8") as handle:
            cloud_apps = json.load(handle)
    rows = audit_addons.inventory(server, cloud_apps)
    return emit(rows, ("key", "name", "version", "vendor", "enabled", "licensed", "finding", "note"), args, out)


MAP_COLUMNS = {
    "users": usermap.COLUMNS, "fields": fieldmap.COLUMNS, "names": namemap.COLUMNS, "options": options.COLUMNS}


def map_rows(kind, server, cloud):
    """Rows for one mapping kind."""
    if kind == "users":
        return usermap.map_users(cloud, audit_users.all_users(server))
    if kind == "names":
        return namemap.map_names(server, cloud)
    server_fields = audit_fields.custom_fields(server)
    if kind == "fields":
        return fieldmap.map_fields(server_fields, fieldmap.cloud_custom_fields(cloud))
    field_rows = fieldmap.map_fields(server_fields, fieldmap.cloud_custom_fields(cloud))
    return options.compare(cloud, options.server_options(server), field_rows)


def map_command(server, cloud, args, out):
    rows = map_rows(args.what, server, cloud)
    if args.output:
        mapfile.write(args.output, mapfile.build(args.what, rows, server.base_url, cloud.base_url))
    emit(rows, MAP_COLUMNS[args.what], args, out)
    return 0


def main(argv=None, server=None, out=None, cloud=None):
    out = out if out is not None else sys.stdout
    args = build_parser().parse_args(argv)
    try:
        server = server or make_server()
        if args.command == "map":
            return map_command(server, cloud or make_cloud(), args, out)
        if args.command == "snapshot":
            snap = snapshot.take(server)
            snapshot.save(args.output, snap)
            out.write("saved {} projects ({} issues) to {}\n".format(len(snap["projects"]), sum(p["issues"] for p in snap["projects"].values()), args.output))
            return 0
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
