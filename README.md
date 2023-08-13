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

    python -m jiramigrate snapshot -o before.json   # per-project counts, to compare with after the migration

    python -m jiramigrate map users -o users.json     # Server username/key -> Cloud accountId, by email
    python -m jiramigrate map fields -o fields.json   # custom fields by name and type
    python -m jiramigrate map names -o names.json     # statuses, issue types, priorities, resolutions
    python -m jiramigrate map options -o options.json # select options missing on Cloud

The map commands need the Cloud settings too. Each writes a JSON mapping file
(`version`, `kind`, `summary`, `items`) next to the table it prints.

    python -m jiramigrate validate counts --snapshot before.json
    python -m jiramigrate validate sample --sample 50 --users-map users.json --names-map names.json
    python -m jiramigrate validate all

With `--cache DIR` the sampled Server issues are kept and reused on the next run. Use it only once the Server is
read-only for the final migration: cached copies are never refreshed.

Validation only prints problems (use `--all-rows` for everything), writes its verdict to
stderr, and exits with 1 when something differs. Sampling is reproducible: the same `--seed`
picks the same issues.

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
