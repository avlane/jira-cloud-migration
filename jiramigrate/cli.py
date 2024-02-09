"""Command line entry point: jira-migrate <command>"""
import argparse
import json
import os
import sys

from . import config, fieldmap, mapfile, namemap, options, report, snapshot, usermap
from .api import Api, ApiError
from .audit import addons as audit_addons
from .audit import bundle as audit_bundle
from .audit import attachments as audit_attachments
from .audit import fields as audit_fields
from .audit import schemes as audit_schemes
from .audit import users as audit_users
from .audit import workflows as audit_workflows
from .validate import cache as validate_cache
from .validate import counts as validate_counts
from .validate import diff as validate_diff
from .validate import run as validate_run
from .validate import summary as validate_summary

FORMATS = ("table", "csv", "json", "markdown")


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
    p_all = audit.add_parser("all", parents=[common], help="run every audit and save each result in a folder")
    p_all.add_argument("--output-dir", "-d", metavar="DIR", help="write <audit>.json for each audit here")
    p_all.add_argument("--cloud-apps", metavar="FILE", help="Cloud availability file for the app audit")
    p_all.add_argument("--limit-mb", type=float, default=audit_attachments.DEFAULT_LIMIT_MB, help="attachment size limit (default 10)")
    audit.add_parser("workflows", parents=[common], help="workflows that no project uses")
    audit.add_parser("schemes", parents=[common], help="permission and notification schemes that no project uses")
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
    validate = top.add_parser("validate", help="compare the Server and Cloud sites after the migration").add_subparsers(dest="what", required=True)
    for name, helptext in (("counts", "issue counts per project"), ("sample", "field-level comparison of sampled issues"), ("all", "both of the above")):
        p = validate.add_parser(name, parents=[common], help=helptext)
        p.add_argument("--project", action="append", metavar="KEY", help="project to check (repeatable); default is every project")
        p.add_argument("--all-rows", action="store_true", help="show passing checks too")
        if name != "counts":
            p.add_argument("--sample", type=int, default=25, metavar="N", help="issues to sample per project (default 25)")
            p.add_argument("--seed", default="1", help="sampling seed; the same seed picks the same issues")
            p.add_argument("--cache", metavar="DIR", help="keep the sampled Server issues here and reuse them next time (only for a frozen Server)")
            p.add_argument("--users-map", metavar="FILE", help="users mapping file from `map users`")
            p.add_argument("--names-map", metavar="FILE", help="names mapping file from `map names` (edit cloudName where you renamed things)")
        if name != "sample":
            p.add_argument("--snapshot", metavar="FILE", help="use the counts recorded by `snapshot` instead of counting the Server again")
    return parser


def make_cloud(prefix="/rest/api/3/"):
    settings = config.cloud_from_env()
    return Api(settings.url, auth=(settings.email, settings.token), prefix=prefix)


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


def audit_all_command(server, args, out):
    cloud_apps = None
    if args.cloud_apps:
        with open(args.cloud_apps, encoding="utf-8") as handle:
            cloud_apps = json.load(handle)
    results = audit_bundle.run_all(server, cloud_apps, args.limit_mb)
    if args.output_dir:
        os.makedirs(args.output_dir, exist_ok=True)
        for name, rows in results.items():
            with open(os.path.join(args.output_dir, name + ".json"), "w", encoding="utf-8") as handle:
                json.dump(rows, handle, indent=2)
                handle.write("\n")
    return emit(audit_bundle.headline(results), ("audit", "rows"), args, out)


def audit_workflows_command(server, args, out):
    rows = audit_workflows.report(server)
    return emit(rows, ("name", "steps", "default", "projects", "lastModified", "finding"), args, out)


def audit_schemes_command(server, args, out):
    return emit(audit_schemes.report(server), ("kind", "id", "name", "projects", "finding"), args, out)


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


def load_context(args):
    """Users and names mappings from the files given on the command line."""
    users, names = {}, {}
    if getattr(args, "users_map", None):
        for item in mapfile.read(args.users_map, "users")["items"]:
            if item.get("accountId"):
                users[item["serverName"]] = item["accountId"]
    if getattr(args, "names_map", None):
        for item in mapfile.read(args.names_map, "names")["items"]:
            if item.get("cloudName") and item["cloudName"] != item["serverName"]:
                names.setdefault(item["kind"], {})[item["serverName"]] = item["cloudName"]
    return validate_diff.Context(users=users, names=names)


def validate_command(server, cloud, args, out):
    rows, sampled = [], 0
    projects = args.project or None
    if args.what in ("counts", "all"):
        recorded = snapshot.load(args.snapshot) if getattr(args, "snapshot", None) else None
        rows.extend(validate_counts.compare(server, cloud, projects, recorded))
    if args.what in ("sample", "all"):
        ctx = load_context(args)
        cache = validate_cache.JsonCache(args.cache) if args.cache else None
        keys = projects or sorted(p["key"] for p in server.get("project"))
        for project in keys:
            found, picked = validate_run.compare_sample(server, cloud, project, args.sample, args.seed, ctx, cache)
            rows.extend(found)
            sampled += len(picked)
    shown = rows if args.all_rows else validate_summary.problems(rows) + [r for r in rows if r["status"] in validate_summary.WARNINGS]
    emit(shown, validate_summary.COLUMNS, args, out)
    totals = validate_summary.summarize(rows, sampled)
    for line in validate_summary.describe(totals):
        print(line, file=sys.stderr)
    return validate_summary.exit_code(rows)


def main(argv=None, server=None, out=None, cloud=None):
    out = out if out is not None else sys.stdout
    args = build_parser().parse_args(argv)
    try:
        server = server or make_server()
        if args.command == "map":
            return map_command(server, cloud or make_cloud(), args, out)
        if args.command == "validate":
            return validate_command(server, cloud or make_cloud("/rest/api/2/"), args, out)
        if args.command == "snapshot":
            snap = snapshot.take(server)
            snapshot.save(args.output, snap)
            out.write("saved {} projects ({} issues) to {}\n".format(len(snap["projects"]), sum(p["issues"] for p in snap["projects"].values()), args.output))
            return 0
        if args.command == "audit" and args.what == "fields":
            return audit_fields_command(server, args, out)
        if args.command == "audit" and args.what == "users":
            return audit_users_command(server, args, out)
        if args.command == "audit" and args.what == "all":
            return audit_all_command(server, args, out)
        if args.command == "audit" and args.what == "workflows":
            return audit_workflows_command(server, args, out)
        if args.command == "audit" and args.what == "schemes":
            return audit_schemes_command(server, args, out)
        if args.command == "audit" and args.what == "addons":
            return audit_addons_command(server, args, out)
        if args.command == "audit" and args.what == "attachments":
            return audit_attachments_command(server, args, out)
    except (config.ConfigError, ApiError) as exc:
        print("error: {}".format(exc), file=sys.stderr)
        return 2
    return 0
