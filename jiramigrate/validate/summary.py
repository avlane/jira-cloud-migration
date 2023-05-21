"""Roll the findings of a validation run up into a verdict."""

PASSING = {"ok"}
WARNINGS = {"unmapped-user"}
COLUMNS = ("check", "subject", "field", "server", "cloud", "status", "note")


def problems(rows):
    return [r for r in rows if r["status"] not in PASSING | WARNINGS]


def summarize(rows, sampled=0):
    """Numbers for the headline: count checks, sampled issues, and how many of each have problems."""
    counted = [r for r in rows if r["check"] == "count"]
    found = problems(rows)
    return {
        "countChecks": len(counted),
        "countProblems": sum(1 for r in found if r["check"] == "count"),
        "sampledIssues": sampled,
        "issuesWithDifferences": len({r["subject"] for r in found if r["check"] == "sample"}),
        "warnings": sum(1 for r in rows if r["status"] in WARNINGS),
        "problems": len(found),
    }


def describe(summary):
    lines = []
    if summary["countChecks"]:
        lines.append("counts: {} compared, {} differ".format(summary["countChecks"], summary["countProblems"]))
    if summary["sampledIssues"]:
        lines.append("sample: {} issues checked, {} with differences".format(summary["sampledIssues"], summary["issuesWithDifferences"]))
    if summary["warnings"]:
        lines.append("warnings: {} (users missing from the mapping)".format(summary["warnings"]))
    lines.append("result: {}".format("PASS" if not summary["problems"] else "FAIL ({} problems)".format(summary["problems"])))
    return lines


def exit_code(rows):
    return 1 if problems(rows) else 0
