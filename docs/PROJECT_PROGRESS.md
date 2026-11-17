# FloodRelief Connect: project plan and consecutive work log

Reference: [project proposal](floodrelief-proposal.pdf).

This file records the project state, the next work, and completed changes in
sequence. Append new work-log entries; keep earlier entries so the next session
can resume from the actual stopping point. A feature is complete only after its
implementation and relevant checks pass.

## Current checkpoint

- Last committed checkpoint: `574b5a4`, the traceable relief-request foundation.
- Current workspace: the in-progress account, review, pledge, and delivery
  changes are completed and tested; dashboards, notifications, private evidence,
  map fallback, and update polling are implemented. Frontend/UI refinement is
  complete with the original theme retained. Changes remain uncommitted.
- Current task: the detailed technology, file/folder and interaction guide is
  complete. Work-log entry 008 records the documentation and source checks.
- Development environment: Django, local `.venv`, SQLite; frontend uses Django
  templates and plain CSS/JavaScript.
- Validation: 82 automated tests pass. The role audit passes 98 layouts and 357
  alignment comparisons; final targeted checks pass 11 layouts and 56 comparisons.
  The full six-stage browser workflow also passes with 53 layout checks and 23
  interactions. Django, migration drift, JavaScript, theme/data and production
  manifest checks pass locally.
- All migrations are applied. All 12 original request IDs and all 33 original
  status events are retained unchanged. Later application activity has brought
  the working data to 13 requests and 39 events, including one original request
  advancing to closed; SQLite integrity is `ok`.
- Local app is running at `http://127.0.0.1:8000/`. Setup and demonstration
  accounts are documented in [README.md](../README.md).
- Latest completed work: [the detailed project guide](PROJECT_GUIDE.md) explains
  technologies, source files, relationships, roles, workflows, frontend behavior,
  configuration and a reading/debugging path. The role and alignment work is
  recorded in entry 007. Live integrations and the controlled pilot remain planned.

## Project plan

Follow the proposal's dependency order, rather than assigning new calendar dates
to its original twelve-week schedule.

| Milestone | Proposal reference | Deliverable and acceptance check | State |
| --- | --- | --- | --- |
| Foundation | Sections 3.1-3.3; weeks 1-4 | Django setup, roles, valid submissions, reference IDs, retained status events | Complete; regression checks pass |
| Review | Sections 3.2-3.4; weeks 5-6 | Staff review queue; verified/rejected/more-information decisions; requester responses; first-action timing | Complete; regression checks pass |
| Support | Sections 3.2-3.3; weeks 7-8 | Approved donors offer/withdraw pledges; staff assign a responder; unauthorized changes fail | Complete; regression checks pass |
| Delivery | Sections 3.3-3.4; week 9 | Ordered delivery stages, optional private proof, recipient confirmation before closure | Complete; regression checks pass |
| Visibility | Sections 3.1, 3.2, 3.5; week 10 | Role dashboards and complete activity lists; in-app notifications; optional Google Maps with a working fallback; near-real-time status visibility | Complete locally; live Maps key pending |
| Validation | Sections 3.4, 6; week 11 | Automated workflow/permission/upload/metric tests; documented pilot tasks and measurements | Automated/browser checks complete; real pilot pending |
| Handover | Week 12 | Accurate setup/demo guide, architecture diagrams, final checkpoint and test evidence | Local handover complete; final presentation follows pilot |
| UI refinement | User follow-up | Clearer navigation, dashboard hierarchy, forms, cards, and mobile usability using the current theme | Complete; automated and browser checks pass |
| Role workspaces and alignment | User follow-up | Distinct beneficiary, donor, NGO, and administrator priorities; aligned cards, metrics, filters, and controls; existing permissions and theme retained | Complete; role, permission, workflow and alignment checks pass |
| Project explanation | User follow-up | Detailed guide to the implemented technologies, files, data relationships and request workflow, with verified source links and a reading path | Complete; source coverage, symbols, routes, links and formatting checks pass |

Implementation decisions from the reference:

- Use `docs/floodrelief-proposal.pdf` as the canonical reference. The root-level
  PDF is a different file and is retained unchanged.
- Keep evidence optional. Protect original evidence and recipient/contact
  details behind account permissions.
- A rejected or more-information review is still a meaningful staff action for
  the acknowledgement metric; keep the request's lifecycle and review decision
  distinct.
- Show duplicate suggestions to staff; never reject automatically.
- Begin notifications inside the app, as section 3.1 explicitly allows. Email
  and SMS remain optional future integrations.
- Keep the core workflow usable without a maps key or an external connection.
- A real pilot, device testing, and production deployment need actual users and
  infrastructure; document those tasks without claiming they have been run.

## Next planned work

1. Configure a restricted Google Maps browser key in `.env` and verify live
   markers and the outage fallback on the intended origins.
2. Run the key workflows on physical low-to-mid range devices and slow/unstable
   connections. Browser viewport checks have passed, but physical devices have
   not been tested.
3. Prepare PostgreSQL staging with persistent private media and backups, verify
   concurrent review/assignment behavior, and complete the hosting/HTTPS setup.
4. Run [PILOT_PLAN.md](PILOT_PLAN.md) with representative roles, collecting the
   median acknowledgement time, confirmation coverage, task errors, clarity
   ratings, and comparison with the informal coordination baseline.
5. Fix observed issues, repeat the affected scenarios, and prepare the final
   report/presentation with measured results.

Email/SMS and multi-responder or partial-fulfilment extensions are optional
future work; the implemented semester prototype records one lead delivery per
request and begins with in-app notifications.

## Consecutive work log

### 001 - 2026-11-17 - Completed: repository and proposal audit

- Read the folder layout, Git status/history, README, settings, and existing
  account/review/support/delivery file inventory.
- Identified substantial unfinished changes already present in the workspace;
  continue those changes in place and retain the existing data.
- Confirmed the requested reference is `docs/floodrelief-proposal.pdf`.
- Created this file before implementation to retain the plan and work sequence.
- Read the canonical proposal's six pages, including its workflow, privacy,
  external-service fallback, test examples, metrics, and twelve-week plan.
- Read the existing services, permissions, migrations, templates, and seed data.
- Baseline checks: Django system check passes; migration files match the models;
  five milestone migration files are unapplied. The local database has 12
  requests and 33 status events; retain these records.
- Found the demo command still calls status transitions without the newly
  required verification/delivery records. Public cards also show free-text
  descriptions and detailed locations that can contain private information.

### 002 - 2026-11-17 - Completed: stabilize the full lifecycle

- Current work: add meaningful workflow and permission tests, finish public-data
  boundaries, repair the demo command for the new service rules, and apply the
  pending schema changes with a database backup.
- Acceptance: a beneficiary, approved donor, and staff account can complete all
  six stages; acknowledgement and delivery confirmation remain measurable; bad
  or unauthorized actions do not leave partial records.
- Implemented optional submission evidence and a public district/town field;
  private descriptions, exact locations, contact information, and evidence stay
  out of public cards and search. Fixed the landing-page preview as well.
- Added 47 automated account/lifecycle/view/demo tests. The first run identified
  the landing preview issue and sandbox restrictions on Windows temporary
  folders used by upload tests; the remaining workflow assertions passed.
- Updated the demo command to use the actual services, create all four demo
  roles, preserve other requests on `--fresh`, and enrich only matching old
  sample records without changing their existing status trail.
- Validation: all 47 account/workflow/view/demo tests pass. Upload tests passed
  after allowing the test command to use Windows temporary folders.
- Backed up SQLite to
  `.local/backups/db-before-continuation-20261117.sqlite3`, then applied the five
  pending milestone migrations and the optional-evidence/location migration.
- Ran the demo command without `--fresh`; existing request records were retained.

### 003 - 2026-11-17 - Completed: supporting visibility features

- Current work: persistent in-app notifications, full paginated activity lists,
  dashboard status summaries, a public map with coarsened positions and a
  dependency-free list fallback, and request-update polling.
- Keep notifications after the core transaction commits and keep all Google
  Maps requests optional so supporting-feature failure cannot block relief work.
- Add tests for notification ownership, commit timing, service failure, map
  privacy, filters, and update visibility before marking this milestone complete.
- Implemented persistent recipient-owned notifications with unread/read controls,
  duplicate-event protection, and callbacks that run after a successful commit.
- Added complete paginated activity records, staff operations filters, stage
  summaries, and the actual delivery-confirmation coverage metric.
- Added optional Google Maps enhancement. Public map data excludes unverified
  and closed requests, private text and contacts, original coordinates, and file
  metadata; positions are rounded to two decimal places. The normal area list
  remains available without a key, JavaScript, or a working external service.
- Added read-only update endpoints and 30-second polling notices. A new update
  does not replace the page's active forms.
- Validation: all 66 automated tests pass; Django checks and JavaScript syntax
  checks pass; no missing migrations. SQLite integrity is `ok`, with the original
  12 requests and 33 events retained.

### 004 - 2026-11-17 - Completed: browser verification and handover

- Current work: check desktop/tablet/phone layouts and a real browser submission,
  review, pledge, assignment, delivery, receipt-confirmation, and inbox flow.
- Use an isolated database and media directory under `.local/` for browser
  checks; keep the working SQLite database unchanged by test scenarios.
- Update the README, use-case mapping, architecture diagrams, pilot plan, test
  report, and final resume checkpoint.
- Completed the full authenticated browser workflow with actual PDF uploads,
  six audit events, inbox read actions, and administrator desk access.
- Verified 20 page/viewport combinations at 360, 768, and 1440 px without
  horizontal overflow. Normal and reduced-motion runs pass; screenshots are
  retained in `.local/verification/`.
- Verified that Maps loading failure leaves the area list usable and that
  polling preserves unsent donor form input.
- Rewrote the README around the implemented behavior, updated the proposal
  use-case mapping, and added architecture/ER/sequence diagrams, a pilot plan,
  and a test report.
- Added `AGENTS.md` so later continuation sessions read this checkpoint and
  append the next consecutive work-log entry.

### 005 - 2026-11-17 - Completed: final verification and resume checkpoint

- Final suite: 66 tests pass; Django and JavaScript checks pass; no migration
  drift; `git diff --check` and documentation link checks pass.
- Confirmed production settings and WhiteNoise manifest static collection with
  a generated verification-only secret. No live PostgreSQL deployment or real
  Maps integration was claimed.
- Corrected acknowledgement wording to include the first review, kept target
  labels consistent with configuration, and fixed the unsaved admin request's
  workflow-link hint.
- Compared the working database directly with its backup: original request
  references/lifecycle timestamps and all 33 original event records are
  retained. No browser test requests were added to the working database.
- Stopped the isolated browser test server and hidden browser. Started the
  normal local app at `http://127.0.0.1:8000/` and checked landing, board,
  submission, map, and login pages successfully.
- Resume from the next planned work above; append entry 006 when starting the
  next task, and retain entries 001-005.

### 006 - 2026-11-17 - Completed: frontend and UI refinement

- User instruction: improve the frontend/UI without changing the theme.
- Review the current pages and retain the existing palette, Fraunces/Archivo/
  JetBrains Mono typography, photography, and plain Django/CSS/JavaScript stack.
- Current work: improve workspace navigation and dashboard hierarchy; reduce
  form clutter; make request cards, status progress, and mobile controls easier
  to scan and use; strengthen focus, labels, and readable helper text.
- Acceptance: existing workflow and privacy boundaries still work; theme tokens
  match the baseline; desktop/tablet/phone layouts and key interactions pass.
- Implemented desktop workspace navigation and native mobile menus, a compact
  account footer, role-aware dashboard actions and personal summary counts.
- Refined form spacing/alignment, optional-detail disclosure, password controls,
  error summaries, private-data guidance, and client feedback. Server validation
  and workflow services remain the authority.
- Refined public board filters/results, request cards, legible lifecycle
  timelines, account pages, and landing-page links/motion.
- Validation completed: 67 automated tests pass; 53 main browser layout checks
  and 12 targeted final checks pass at 320, 360, 768, and 1440 px. The complete
  six-stage workflow, real uploads, privacy checks, inbox, map fallback, and
  polling preservation pass through the refined UI.
- Passed 29 focused browser interaction checks, including native menus,
  keyboard/focus handling, password controls, optional disclosure, server and
  courtesy error feedback, and no-JavaScript paths. No uncaught app JavaScript
  exceptions were recorded.
- Corrected phone grid overflow that earlier `window.innerWidth` checks missed,
  cramped mobile action buttons, and radio-group error links. Restarted the
  isolated server after final template edits to verify refreshed markup.
- Theme definitions match the saved baseline exactly; the original 12 requests
  and 33 audit events match the backup, with SQLite integrity `ok`.
- Updated README and test evidence. Refreshed the normal preview at
  `http://127.0.0.1:8000/` with autoreloading so future template edits refresh.
- Local screenshots and the combined browser report are retained in
  `.local/verification/ui/`. Browser checks use an isolated database and media
  directory; no test requests were added to the working database.
- Final file checks pass. Production manifest collection includes the refined
  CSS/JavaScript assets. Landing, board, submission, login, and map preview
  pages return HTTP 200 and serve refreshed templates.
- Fresh final regression run: all 67 tests pass with no Django system-check
  issues. Stopped the isolated verification server and browser; the normal
  preview remains running and its landing page returns HTTP 200.
- Resume from the next planned work above. Append entry 007 for the next task,
  retaining entries 001-006 and the proposal-based project plan.

### 007 - 2026-11-17 - Completed: role workspaces and consistent alignment

- User instruction: clarify the differences between beneficiary/donor and
  NGO/administrator workspaces; clean up uneven boxes and interface alignment
  while preserving the existing theme.
- Started by reading the current checkpoint, role rules, dashboard/navigation
  templates, shared styles, existing tests, and browser verification tools.
- Confirmed the demo accounts have their correct roles and permissions. The
  shared menu/dashboard obscures those differences; request-card footer and
  metric layouts also depend on content length.
- Plan: introduce role-focused dashboards and navigation, expose authorized
  account/approval tools in the administrator workspace, refine activity defaults,
  and use consistent responsive card, metric, toolbar, and control layouts.
- Acceptance: each role sees its own primary tasks; pending donors have a clear
  approval state; account actions enforce existing administration permissions;
  private records remain protected; all four role views and key public/form
  screens align at desktop/tablet/phone widths with the original theme retained.
- Verify relevant role/permission regressions, the full existing test suite,
  Django/migration/JavaScript checks, and browser layout/interaction behavior.
  Keep browser scenarios separate from the working database.
- Implemented distinct dashboards, primary actions and navigation for all four
  roles. Pending donors keep their support workspace with a clear approval state.
- Added account oversight and donor approval using existing Django view/change
  user permissions, CSRF-protected POST actions and after-commit notifications.
  Donor approvals preserve identity, roles, privileges and other accounts.
- Activity opens personal pledges for donors and operations for coordinators;
  beneficiary records remain personal. Donor discovery displays/searches public
  areas before assignment, protecting private addresses.
- Aligned cards, footers, summary values and filter controls; removed staggered
  landing role cards. Corrected a 320 px acknowledgement-label clipping issue
  detected by checking card content as well as outer viewport bounds.
- Validation: 20 focused checks and the complete 82-test regression suite
  pass. The full suite required the previously authorized Windows upload-test
  temporary-directory access. Django checks and migration drift checks pass.
- Browser audit: 98 layouts, 357 alignment comparisons and 18 role/approval/menu
  interactions pass. The native account approval works without JavaScript, and
  no uncaught app JavaScript errors were recorded.
- Read-only data audit: all 12 original request IDs and all 33 original audit
  events are retained. Current app data has 13 requests and 39 events, including
  one original request that has since completed its lifecycle. Retain this
  later activity; no isolated role-UI accounts were added to the working DB.
- Completed the full six-stage browser workflow with actual evidence/proof PDF
  uploads, six ordered audit events, committed notifications, private-contact
  restrictions, Maps fallback and polling that preserves unsent form input.
  This run passes 53 layout checks and 23 interactions.
- Final refinements keep account-table actions inline, metric link arrows
  together, and show a direct Confirm receipt action on owned delivered cards.
  The table adapts to its container while preserving accessible table semantics.
- Final targeted browser checks pass 11 layouts, 56 alignment comparisons and
  two interactions. Account-table semantics pass at 320, 360, 768, 1024, 1040,
  1200 and 1440 px. The receipt check uses complete delivered activity because
  the dashboard intentionally previews only the six most recent requests.
- The final visual review corrected an orphaned arrow in the phone account
  summary. Repeated all 11 targeted layouts/56 comparisons successfully, and
  all nine focused account-management tests pass after that template refinement.
- Production manifest collection includes the final frontend assets. Theme
  definitions still match the saved baseline exactly. Web fonts and Maps were
  blocked during browser checks; live integrations and physical devices were
  not verified.
- Updated README setup/role/approval guidance, the test report and proposal
  route mapping. Reports and screenshots are retained in
  `.local/verification/roles-ui/`, `.local/verification/roles-ui-workflow/`
  and `.local/verification/roles-ui-final/`.
- Stopped the isolated verification server and hidden browser. The normal
  preview remains at `http://127.0.0.1:8000/`; landing, board, login and the
  updated workspace stylesheet return HTTP 200. The final read-only theme/data
  audit passes with all original records retained.
- Resume from the next planned work above. Append entry 008 for the next task,
  retaining entries 001-007 and the proposal-based project plan.

### 008 - 2026-11-17 - Completed: detailed project explanation

- User instruction: create a detailed file/report explaining each folder/file,
  the technologies used and how the parts interact so the project is easier to
  understand.
- Read the workspace guide, existing checkpoint, Git status and source inventory.
  Retain all existing implementation changes and working data.
- Plan: create `docs/PROJECT_GUIDE.md` with a beginner-friendly architecture
  explanation, file responsibility tables, route/model relationships, complete
  lifecycle examples, frontend behavior, permissions, configuration, testing
  guidance and a recommended reading order. Link it from the README.
- Acceptance: explanations match the implemented code rather than a generic
  Django scaffold; important source paths and functions are linked; development
  and optional/production technologies are clearly identified; document links,
  coverage and formatting checks pass. This task changes documentation only.
- Read the current settings, dependency declarations, models, forms, services,
  routes, permissions, signal handlers, templates, frontend scripts, migration
  operations and existing verification documents.
- Created the 16-section guide with a complete authored-file map, explanations
  of shared package markers/generated folders, architecture/entity/sequence
  diagrams, a six-stage worked example and a seven-action service map.
- Explained session authentication, account approval, public/private data and
  attachments, transactions, after-commit notifications, map fallback, polling,
  CSS/JavaScript connections, configuration, migrations and test/demo files.
- Added practical change-location tables, a reading/debugging path and glossary.
  Linked the guide from the README and current checkpoint.
- Static documentation validation passes: all 141 existing source,
  configuration/documentation and asset files are covered; 50 named symbols and
  all 24 routes match the source. Relative links, 17 heading fragments and all
  17 code/diagram block boundaries pass. Evidence is retained in
  `.local/verification/project-guide/documentation-report.json`.
- The application regression evidence remains the 82-test result from entry 007.
  This documentation task uses source/link/format checks and preserves the
  working application and its existing data.
- Resume from the next planned work above. Append entry 009 for the next task,
  retaining entries 001-008 and the proposal-based project plan.
