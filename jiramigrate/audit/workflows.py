"""Workflow audit: workflows no project uses.

Server and Data Center have no REST call that lists workflow schemes, so usage is worked out
from what each project is assigned. Schemes that no project uses cannot be seen this way; look
at Administration > Workflow schemes for those.
"""
from ..api import ApiError


def projects(server):
    return server.get("project")


def workflows(server):
    return server.get("workflow")


def project_workflow_schemes(server, skipped=None):
    """Map project key -> its workflow scheme.

    Archived projects and projects the account cannot see answer 403 or 404; their keys are added to
    `skipped` (if given) instead of stopping the audit.
    """
    found = {}
    for project in projects(server):
        try:
            found[project["key"]] = server.get("project/{}/workflowscheme".format(project["key"]))
        except ApiError as exc:
            if exc.status not in (403, 404):
                raise
            if skipped is not None:
                skipped.append(project["key"])
    return found


def scheme_workflows(scheme):
    """Names of every workflow a scheme can use: the default plus any per-issue-type ones."""
    return {scheme["defaultWorkflow"], *scheme.get("issueTypeMappings", {}).values()}


def report(server):
    used = {}
    skipped = []
    schemes = project_workflow_schemes(server, skipped)
    for key, scheme in schemes.items():
        for name in scheme_workflows(scheme):
            used.setdefault(name, []).append(key)
    rows = []
    for flow in workflows(server):
        keys = used.get(flow["name"], [])
        rows.append({"name": flow["name"], "steps": flow.get("steps", 0), "default": bool(flow.get("default")),
                     "projects": keys, "lastModified": flow.get("lastModifiedDate", "")[:10],
                     "finding": "" if keys or flow.get("default") else ("maybe-unused" if skipped else "unused")})
    for key in skipped:
        rows.append({"name": "(project {})".format(key), "steps": 0, "default": False, "projects": [key], "lastModified": "",
                     "finding": "project-unreadable"})
    return rows
