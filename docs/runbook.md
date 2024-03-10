# Migration runbook

The order in which the pieces are meant to be used around a Cloud Migration Assistant run.

## Weeks before

1. `jira-migrate audit all -d audit/` and work through the files: merge duplicate custom fields,
   delete unused workflows and schemes, give every real person an email address, decide what to do
   with attachments over your Cloud limit, and look up each installed app (`audit addons
   --cloud-apps cloud-apps.json`).
2. `jira-migrate map users -o users.json` and fix the `missing`, `ambiguous` and `no-email` rows
   (usually by correcting the email on Server or inviting the person to Cloud).
3. `jira-migrate map fields`, `map names` and `map options`. Make the Cloud site match: create the
   fields, statuses and options that are reported missing, or edit `cloudName` in the names file
   where a Server name is meant to land on a differently named Cloud one.

## Just before the final run

4. Make the Server read-only and take the baseline: `jira-migrate snapshot -o before.json`.

## After the run

5. `jira-migrate validate counts --snapshot before.json`.
6. `jira-migrate validate sample --sample 50 --users-map users.json --names-map names.json --cache cache/`.
   Raise `--sample` for the projects that matter most. The same `--seed` picks the same issues, so a
   re-run after a fix compares like with like.
7. Anything reported as `missing-on-cloud`, `missing-link`, a count mismatch or a text difference is
   worth looking at issue by issue before users are told the site is ready.

## Notes

- Sites with an internal certificate authority: set `REQUESTS_CA_BUNDLE` to the bundle file.
- Data Center 8.14 and later can use a personal access token (`JIRA_SERVER_TOKEN`).
- Server reached end of support on 2024-02-15; plan the move before the next security advisory.
