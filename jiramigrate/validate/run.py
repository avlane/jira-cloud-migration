"""Run the sampled comparison for a project."""
from . import diff, sample


def compare_sample(server, cloud, project, n, seed, ctx):
    """Compare n sampled issues of a project. Returns (difference rows, keys that were sampled)."""
    keys = sample.pick_keys(server, project, n, seed)
    theirs = sample.fetch_issues(server, keys)
    ours = sample.fetch_issues(cloud, keys)
    rows = []
    for key in keys:
        rows.extend(diff.compare_issue(theirs[key], ours[key], ctx))
    return rows, keys
