# FloodRelief Connect workspace guide

- Read `docs/PROJECT_PROGRESS.md` before starting work. Use
  `docs/floodrelief-proposal.pdf` as the canonical project reference.
- Keep the Markdown work log consecutive: append the next numbered entry with
  the date, work started, and acceptance checks; record completion and actual
  validation results, then update the current checkpoint and project plan.
- Inspect Git status before editing and retain existing unfinished work and
  local data. Demo refreshes must affect matching fictional samples only.
- Continue the Django and plain HTML/CSS/JavaScript architecture. Use the
  request, verification, donation, and delivery services for workflow changes.
- Preserve ordered status history, first-action acknowledgement timing,
  approval permissions, recipient confirmation, and private evidence routes.
- Maps and notifications must remain optional supporting features. Public
  views must not contain private descriptions, contacts, exact addresses,
  original coordinates, review notes, or attachment metadata.
- Run checks and tests appropriate to changes. For workflow/schema changes,
  use Django checks, the relevant tests, and the migration drift check. Keep
  test scenarios separate from the working database.
- Update the README and test report when behavior or verified coverage changes.
  Distinguish automated/browser checks from live integrations, physical-device
  checks, and a real pilot.
