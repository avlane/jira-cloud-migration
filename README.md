# jira-cloud-migration

Helpers for moving a Jira Server / Data Center site to Jira Cloud. Atlassian ends support
for Jira Server on 2024-02-15, so the aim is a set of repeatable checks around the Cloud
Migration Assistant rather than a replacement for it:

1. audits to run on the Server side before the migration (duplicate custom fields,
   unused workflows and schemes, users without an email address, oversized attachments,
   apps),
2. mapping files from Server usernames and fields to their Cloud equivalents,
3. validation after the migration (issue counts, sampled field-level comparisons,
   attachment and comment counts, links).

Status: just started. Audits first.

## Usage

    python -m jiramigrate audit fields            # duplicate custom fields
    python -m jiramigrate audit fields --unused   # fields no issue uses (one search per field)
    python -m jiramigrate audit users             # users without a usable email address

    python -m jiramigrate audit attachments --limit-mb 20

Every audit takes `--format table|csv|json`.

## Configuration

Server or Data Center (read-only access is enough, an administrator for the app inventory):

    export JIRA_SERVER_URL=https://jira.corp.example.com
    export JIRA_SERVER_USER=svc-migration
    export JIRA_SERVER_PASSWORD=...
    # or, on Data Center 8.14 and later, a personal access token:
    export JIRA_SERVER_TOKEN=...

Cloud (used by the mapping and validation steps):

    export JIRA_CLOUD_URL=https://example.atlassian.net
    export JIRA_CLOUD_EMAIL=you@example.com
    export JIRA_CLOUD_API_TOKEN=...
