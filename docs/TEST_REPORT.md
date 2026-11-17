# Local validation report

Date: 2026-11-17. Reference: proposal sections 3.4 and 6.

## Automated regression checks

Result: **82 tests passed** with Django 5.2.17, Python 3.13, and an isolated
SQLite test database.

~~~powershell
.\.venv\Scripts\python.exe manage.py test --noinput
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
~~~

| Area | Verified behavior |
| --- | --- |
| Accounts | Hashed passwords, permitted registration roles, pending donor approval, case-insensitive email login, safe next URL, inactive-account denial, POST-only logout |
| Account management | Active staff plus view/change-user permissions; role labels grant no account access; read-only reviewers cannot approve; CSRF-protected POST-only approval preserves identity/privileges, is idempotent and notifies after commit; filters and pagination work |
| Submission | Valid input receives a unique reference and initial event; invalid input leaves no record; optional coordinate pairs/ranges are validated |
| Review | Staff-only decisions, rejected/more-information history, owner-only responses, stale-review rejection, first acknowledgement retained |
| Support | Approval required at pledge and assignment, positive quantities, INR funds, donor-only withdrawal, no assignment of withdrawn/wrong-request pledges |
| Delivery | Correct stage order, assigned responder/staff permissions, hand-over information required, recipient confirmation required before closure |
| Audit and metrics | Six retained lifecycle events, correct actors, median first-action calculation, within-target/overdue counts, real recipient-confirmation coverage |
| Evidence | Size/extension/signature validation, private requester/reviewer downloads, private delivery proof, attachment response, missing/public files denied |
| Authorization | Unauthorized dashboards/actions/records denied; CSRF required; personal activity cannot be broadened by URL scope |
| Public information | Private description/address/contact search and display prevented; maps contain verified active needs and rounded coordinates only |
| Notifications | Recipient ownership, after-commit timing, rollback suppression, event deduplication, approval updates, disabled/failing notifications do not undo relief actions |
| Visibility | Complete paginated activity, status/pledge revision updates, read-only uncached snapshots, owner-scoped dashboard totals |
| Role workspaces | Distinct role priorities/menus; pending donors retain support workspace; donor activity defaults to personal pledges; coordinators default to operations with explicit personal scope; donor discovery excludes private addresses |
| Demo command | Idempotent seed, four role accounts, linked historical records, preserved non-demo requests on refresh, production credential seeding refused |

The first test run found a private address in the landing-page preview, which
was corrected. Upload tests initially encountered sandbox restrictions on
Windows temporary folders; the approved test run verified their behavior.

## Browser validation

Used a hidden Edge browser with separate beneficiary, staff, donor, and
administrator sessions. All browser test data and files were stored under
`.local/` in a separate database/media directory.

The browser completed:

1. Beneficiary login and request submission with an actual PDF attachment.
2. Staff verification with method/notes.
3. Approved donor pledge.
4. Staff assignment to that pledge.
5. Assigned responder start and hand-over with an actual proof attachment.
6. Beneficiary receipt confirmation and closure.
7. Verification of all six audit events.
8. Committed inbox updates and mark-all-read action.
9. Administrator coordination-desk access.
10. Update notice while a donor had unsent form input; the input was retained.
11. Blocked Google Maps loading; the verified area list remained available.

No uncaught JavaScript exceptions were recorded.

Twenty page/viewport checks found no horizontal overflow:

| Pages | Widths checked |
| --- | --- |
| Landing, request form, registration, public board, map | 360, 768, 1440 px |
| Closed request, verification queue, complete activity | 360 px |
| Staff dashboard | 360, 1440 px |

Both normal and reduced-motion browser runs completed. Local screenshots and
the detailed browser report are in `.local/verification/`. External web fonts
and Maps requests were blocked during these checks; fallback layout and
dependency failure were intentionally exercised.

## UI refinement validation

The frontend refinement retains the complete original `:root` definitions,
including palette, fonts, photography paths, grain, and metrics. They match
`.local/ui-theme-baseline.css` exactly. The original image files are unchanged.

The isolated Edge run completed **53 layout checks**, followed by **12 targeted
checks** after the final mobile-button and form-label refinement. Width checks
compare document and visible field/panel bounds with the actual viewport;
mobile overflow cannot pass simply by widening `window.innerWidth`.

| Screens | Widths checked |
| --- | --- |
| Landing, submission, login, registration, public board, area map | 360, 768, 1440 px |
| Submission, login, public board | Additional 320 px checks |
| Beneficiary and staff dashboards | 320, 360, 768, 1440 px |
| Donor dashboard, support, verification, activity, notifications | 360, 768, 1440 px |
| Review form and closed request with full timeline | 360, 768, 1440 px |
| No-JavaScript staff dashboard | 360 px |
| Landing and board with normal motion | 1440 px |

All checked screens fit the viewport. The browser also passed 29 focused
interaction checks across the main and final runs: native mobile menus,
desktop/sidebar resizing, Escape and focus return, independent password
visibility, optional information, retained invalid values, linked error
summaries, urgency feedback, readable paired inputs, and dismissible messages.
Navigation, optional information, and server validation also work without
JavaScript.

The complete submission/review/pledge/assignment/delivery/receipt workflow was
repeated through the refined screens with actual evidence and proof uploads.
All six audit events were retained, contact details remained restricted before
assignment, notification read actions passed, Maps failure retained the area
list, and polling preserved unsent donor input. No uncaught app JavaScript
exceptions were recorded. Normal and reduced-motion behavior were exercised.

Browser checks found and corrected a phone submission-grid overflow and cramped
primary buttons. The test server was restarted after final template edits to
refresh Django's template cache, and the affected screens were checked again.
Final screenshots and the combined report are in `.local/verification/ui/`.
Web fonts and Maps requests were blocked during browser checks; physical-device
and live-integration validation remain listed below.

## Role workspaces and alignment validation

The follow-up adds 15 meaningful role/account regressions to the previous
67-test suite. All 82 tests pass; the initial 20 focused checks also passed.
Workflow services, role permissions, privacy boundaries and the theme remain
intact. All nine account-management tests passed again after the last
template refinement.

The main isolated Edge audit passes **98 layouts**, **357 alignment
comparisons** and **18 role/approval/menu interactions**. It compares card
heights and footers, metric values, filter controls, account rows and viewport
bounds. No alignment failures or uncaught app JavaScript exceptions were
recorded.

| Screens | Widths checked |
| --- | --- |
| Public pages, role dashboards, support, review, activity and account management | 320, 360, 768, 1440 px |
| Dashboard transitions | Additional 390, 1024, 1040 px checks |
| Pending donor and read-only account reviewer | 360, 1440 px |
| Final account-table accessibility and layout | 320, 360, 768, 1024, 1040, 1200, 1440 px |

Beneficiaries see personal request actions, donors see pledges and assigned
deliveries, NGO staff see review/assignment priorities, and administrators see
account oversight. Pending donors keep their support workspace. The browser
verified donor approval through a native CSRF-protected form without JavaScript,
the committed approval notification, read-only account access and denial of
account management for NGO staff without user-management permissions.

The complete six-stage workflow was repeated with actual evidence/proof PDF
uploads, six ordered audit events, private-contact restrictions, inbox actions,
Maps fallback and polling that preserves unsent donor input. This run passes
**53 layout checks** and **23 interactions** with no application JavaScript
exceptions.

After final table/action/card refinements, **11 targeted layouts**, **56
alignment comparisons** and **two interactions** pass. The account table retains
accessible table semantics at all seven checked widths, and owned delivered
requests expose a direct **Confirm receipt** link. The receipt check uses the
complete delivered activity list because the dashboard is a six-request preview.

Local screenshots and reports:

- `.local/verification/roles-ui/browser-report.json`
- `.local/verification/roles-ui-workflow/browser-report.json`
- `.local/verification/roles-ui-final/browser-report.json`

Web fonts and Maps were blocked during these browser checks. These results
cover browser viewports and fallbacks; physical devices and live integrations
remain planned.

## Project guide documentation validation

[PROJECT_GUIDE.md](PROJECT_GUIDE.md) explains the implemented technologies,
folder/file responsibilities and interaction paths in 16 sections.
Static documentation checks confirm coverage of all 141 existing source,
configuration/documentation and asset files, with shared package markers
explained together. Fifty named symbols and all 24 routes match the source;
relative links, 17 heading fragments and 17 code/diagram block boundaries pass.

The local check report is
`.local/verification/project-guide/documentation-report.json`.
The 82-test regression result above is from work-log entry 007; entry 008
records the documentation checks.

## Environment and data checks

- Django system checks pass and there is no migration drift.
- JavaScript syntax checks pass.
- Production settings load with a verification-only generated secret, and
  WhiteNoise manifest static collection completes. No real credentials were
  changed or printed. Manifest collection was repeated after UI refinement and
  includes every new/updated frontend asset. It passed again after the final
  role/alignment changes.
- The original working SQLite database was backed up at
  `.local/backups/db-before-continuation-20261117.sqlite3` before migration.
- All pending schema changes were applied. The latest read-only audit confirms
  all **12 original request IDs** and **33 unchanged original status events**
  remain. Later application activity has brought the working database to
  **13 requests and 39 events**, including one original request advancing to
  closed. No isolated role-UI accounts exist in it; SQLite integrity is `ok`.
- Older matching demonstration requests were enriched with linked review and
  delivery records; non-demo entries were retained.

## Validation still to run

- Live Google Maps rendering with a restricted real browser key.
- Physical low-to-mid range devices and slow/unstable connections.
- PostgreSQL staging, including concurrent review/assignment behavior.
- The representative-role controlled pilot and comparison with an informal
  coordination baseline.
- Production hosting, persistent media backups, and final operational setup.

These are planned validation tasks. The local automated/browser results do not
establish real pilot acknowledgement performance or production readiness.
Use [PILOT_PLAN.md](PILOT_PLAN.md) to collect the proposal's measurements and
[PROJECT_PROGRESS.md](PROJECT_PROGRESS.md) to continue the numbered work record.
