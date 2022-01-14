"""Workflow audit: workflows no project uses.

Server and Data Center have no REST call that lists workflow schemes, so usage is worked out
from what each project is assigned. Schemes that no project uses cannot be seen this way; look
at Administration > Workflow schemes for those.
"""


def projects(server):
    return server.get("project")


def workflows(server):
    return server.get("workflow")


def project_workflow_schemes(server):
    """Map project key -> its workflow scheme."""
    return {p["key"]: server.get("project/{}/workflowscheme".format(p["key"])) for p in projects(server)}


def scheme_workflows(scheme):
    """Names of every workflow a scheme can use: the default plus any per-issue-type ones."""
    return {scheme["defaultWorkflow"], *scheme.get("issueTypeMappings", {}).values()}


def report(server):
    used = {}
    schemes = project_workflow_schemes(server)
    for key, scheme in schemes.items():
        for name in scheme_workflows(scheme):
            used.setdefault(name, []).append(key)
    rows = []
    for flow in workflows(server):
        keys = used.get(flow["name"], [])
        rows.append({"name": flow["name"], "steps": flow.get("steps", 0), "default": bool(flow.get("default")),
                     "projects": keys, "lastModified": flow.get("lastModifiedDate", "")[:10],
                     "finding": "" if keys or flow.get("default") else "unused"})
    return rows
