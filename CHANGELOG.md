# Changelog

## 1.0.0

- Validation: counts per project (issues, attachments, resolved, assigned), reproducible samples
  that always include the oldest and newest issue, field-level comparison with user and name
  mappings, comment, attachment, time and link checks, `--strict`, `--cache`.
- `audit all` writes one JSON file per audit.
- Markdown output; clearer messages for 401, 403 and 404; unreadable projects no longer stop audits.

## 0.5

- Mapping files for users (by email), custom fields, names and select options.
- `snapshot` records per-project counts before the final migration run.

## 0.1

- Audits: duplicate and unused custom fields, users without usable email addresses, oversized
  attachments, unused workflows and schemes, installed apps.
