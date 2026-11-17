# FloodRelief Connect

A Django platform for one traceable flood-relief record:
**Received → Verified → Assigned → In progress → Delivered → Closed**.

Built against [the project proposal](docs/floodrelief-proposal.pdf) by Ranveer
Singh (1024170100), Manshaan Singh (1024170110), and Jaskanwardeep Singh
(1024170093), submitted to Sandeep Kaur.

The core workflow and supporting visibility features are implemented. See
[the project plan and consecutive work log](docs/PROJECT_PROGRESS.md) for the
current checkpoint and next work, and [the test report](docs/TEST_REPORT.md)
for verified behavior and remaining pilot checks.

For a detailed explanation of the technologies, folders, files and how they
work together, read [the project guide](docs/PROJECT_GUIDE.md).

## Run locally on Windows

Python 3.13 is the development baseline; the existing environment uses Django
5.2.17. Run these commands from the project folder in PowerShell:

~~~powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
if (-not (Test-Path -LiteralPath .env)) {
    Copy-Item -LiteralPath .env.example -Destination .env
}
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed_demo
.\.venv\Scripts\python.exe manage.py runserver
~~~

Open <http://127.0.0.1:8000/>. If the environment already exists, skip creating
it and retain the existing `.env` and database.

On macOS/Linux, create and activate `.venv`, then use `python manage.py ...`.
For a real administrator account, run `python manage.py createsuperuser`.

### Demonstration accounts

All four demonstration accounts use password **`floodrelief`**. The seed command
is restricted to `DEBUG=True` and preserves existing account passwords.

| Account | Role |
| --- | --- |
| `victim@floodrelief.test` | Beneficiary: submit, respond to reviews, confirm receipt |
| `donor@floodrelief.test` | Approved donor: pledge support and update assigned deliveries |
| `staff@floodrelief.test` | NGO staff: verify, assign, coordinate, confirm phone entries |
| `admin@floodrelief.test` | Administrator: account oversight, donor approvals, and relief operations overview |

`seed_demo` creates nine fictional requests with meaningful backdated timestamps
and linked review, support, and delivery records. Re-running it is idempotent.
It enriches matching older sample rows while retaining their references and
status history. `seed_demo --fresh` rebuilds **matching sample requests only**;
other requests and accounts are retained.

## Complete demonstration flow

1. Sign in as the beneficiary and submit a request. Open **Add optional
   information** for evidence or map coordinates; these can be left empty.
   The reference and first audit event appear
   immediately in the request workspace.
2. Sign in as staff, open the verification queue, and record a verified decision
   with the method and notes. Rejected and more-information decisions remain in
   review history; a beneficiary can respond to a more-information review.
3. Sign in as the approved donor, browse verified requests, and offer goods,
   transport, or an INR funds pledge.
4. Staff open that request and assign one available pledge to its responder.
5. The assigned responder starts delivery, then records the recipient and
   hand-over confirmation. A JPEG, PNG, or PDF proof is optional.
6. The beneficiary confirms receipt with the checkbox and notes. Staff can
   record the recipient's phone/in-person confirmation for anonymous requests.
   Closure requires this confirmation.

The request has six timestamped lifecycle events. The selected pledge becomes
delivered, review history remains available, and account notifications record
the relevant updates. One pledge is assigned as the lead delivery for a request;
additional offers stay recorded and can be withdrawn while unassigned. Funds
are recorded as pledges; the platform does not collect payments.

### Account approvals

Public registration offers beneficiary and donor roles. A new donor keeps a
support dashboard with a clear pending-approval message. An authorized
administrator opens **Manage accounts**, reviews **Pending donors** at
`/accounts/manage/`, and selects **Approve donor**. The existing **Support
approved** control in `/admin/users/user/` remains available.

Account oversight requires an active account with `is_staff` and
`users.view_user` or `users.change_user`; approval requires
`users.change_user`. A role label alone does not grant account-management
permissions. Superusers have the required permissions.

Administrators create staff accounts with the NGO staff or administrator role.
Those roles grant relief coordination permissions. Django admin access also
requires `is_staff` and the relevant Django permissions, or a superuser account.

Anonymous submissions remain supported: keep the reference, track the public
status, and coordinate with staff by phone. Signing in before submission links
the request to the beneficiary's private dashboard and review-response forms.

## Pages

| URL | Purpose |
| --- | --- |
| `/` | Landing page and real acknowledgement statistics |
| `/accounts/register/`, `/accounts/login/` | Registration and email login |
| `/accounts/manage/` | Authorized account oversight and donor approval |
| `/dashboard/` | Distinct beneficiary, donor, NGO, and administrator workspaces |
| `/dashboard/activity/` | Complete paginated records with role-specific defaults |
| `/dashboard/notifications/` | Private inbox with unread/read controls |
| `/requests/new/` | Relief request submission |
| `/requests/` | Public status board with filters and audit timestamps |
| `/requests/<uuid>/` | Authorized request workflow and private records |
| `/verification/` | Staff-only review queue, oldest/most urgent first |
| `/support/` | Verified requests awaiting support |
| `/map/` | Public approximate-area map and working area-list fallback |
| `/admin/` | User management and retained workflow records |

Beneficiary activity opens personal requests; donor activity opens personal
pledges. NGO staff and administrators start with **All operations** and can
switch to **My records**. Other users always see their own records, even if an
operations scope is added to the URL.

Beneficiary dashboards focus on requests, review responses and receipt
confirmation. Donors see verified needs, their pledges and assigned deliveries.
NGO staff see the review queue, assignment priorities and delivery coordination.
Administrators see account summaries, donor approvals and operations oversight.

## Workflow rules and privacy

Status transitions commit the request and its audit event together. Services
collect the supporting records, check roles, lock the current request row, and
enforce the stage order. Admin status fields and retained review/support/delivery
records are read-only; workflow links and the authorized verification action
use the services.

| Viewer | Visible information |
| --- | --- |
| Public | Reference, category, public district/town, urgency, scale, status, timestamps |
| Beneficiary | Own private description, contacts, evidence, review history and confirmation |
| Approved donor | Verified needs, own pledges, and assigned delivery records |
| Assigned responder | Delivery contact details and proof for the assigned request |
| Authorized staff | Review queue, private evidence, coordination actions and operations records |

Public cards and search do not expose free-text descriptions, detailed addresses,
contact names/phones, review notes, or original attachments. Review evidence is
limited to its requester and staff. Delivery proof is limited to the requester,
assigned responder, and staff. Private files use authenticated attachment routes;
the project does not publish `/media/` as a public route.

Uploads are optional and validated for a 5 MB maximum, JPEG/PNG/PDF extension,
and matching file signature. Staff duplicate suggestions compare category and
location; they never reject automatically.

### Primary evaluation metric

`acknowledged_at` records the **first meaningful staff review**, including a
rejection or request for more information. Subsequent reviews and delivery stages
do not reset it. The metric measures minutes from submission to that first
action; the headline is the median, with within-target and overdue counts.

`ACKNOWLEDGEMENT_TARGET_HOURS` defaults to `2`. The proposal's pilot target is
a median below two hours. Fictional seed data and automated checks demonstrate
the calculation; they are not a completed pilot.

Staff dashboards also measure the percentage of delivered support records with
recipient confirmation.

### Supporting features

In-app notifications cover review decisions, support offers, assignments,
delivery stages, and donor approval changes. Each recipient gets at most one
notification for a given event. Delivery runs after the core transaction commits;
notification failures are logged without undoing relief work.

The board and authorized request pages check for changes every 30 seconds while
visible. An update notice reports fresh activity and offers refresh, preserving
any unsent form input.

To enable the interactive map, set `GOOGLE_MAPS_API_KEY` in `.env` to a browser
key for the **Maps JavaScript API**, restricted to the intended website origins
and API. The map loads only when requested. It shows verified active requests,
rounds coordinates to two decimal places, and omits private text and contacts.
The area list remains usable without a key, JavaScript, or an available maps
service. Requests without coordinates still appear in the list.

`ENABLE_IN_APP_NOTIFICATIONS=False` disables creation of new updates while the
relief workflow remains available. Email and SMS are future optional extensions.

## Verification and project documents

~~~powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py test --noinput
~~~

The suite currently has **82 passing tests**. The role/UI audit passes 98 layout
checks and 357 alignment comparisons, followed by 11 targeted layouts and 56
comparisons. The full authenticated workflow was repeated with real uploads,
53 layout checks, 23 interactions, notification read actions and Maps fallback.
Role-specific menus, permission checks, native donor approval, accessible table
semantics and receipt links pass. See the test report for coverage and limits.

- [Consecutive work log and project plan](docs/PROJECT_PROGRESS.md)
- [Detailed project and code guide](docs/PROJECT_GUIDE.md)
- [Test report](docs/TEST_REPORT.md)
- [Controlled pilot plan](docs/PILOT_PLAN.md)
- [Architecture, ER, and workflow diagrams](docs/diagrams/architecture.md)
- [Proposal use-case mapping](docs/diagrams/README.md)

The frontend uses Django templates and plain HTML/CSS/JavaScript, with no build
step. It retains the original water/sand/amber palette, Fraunces/Archivo/
JetBrains Mono typography, photography, wave mark, and grain. Account pages
use a desktop sidebar and a compact native mobile menu. Cards use consistent
heights, footers and spacing; metrics and filters align across responsive rows.
Dashboards provide distinct role actions and summaries; submission keeps
optional information collapsed until needed, with readable labels and linked
error summaries.

Use the normal development server with autoreloading. Restart servers started
with `--noreload` after Python or template changes so cached templates refresh.
Existing photography credits remain in
[static/images/CREDITS.md](static/images/CREDITS.md).

## Production setup

Set `DJANGO_SETTINGS_MODULE=config.settings.production` in the process
environment, and configure `SECRET_KEY`, `ALLOWED_HOSTS`, PostgreSQL settings,
and HTTPS settings using `.env.example` as the reference. Production startup
rejects a missing/development secret or empty allowed-host list.

~~~powershell
$env:DJANGO_SETTINGS_MODULE = "config.settings.production"
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py collectstatic --noinput
~~~

Use a production WSGI/ASGI server; Gunicorn is included for non-Windows systems.
WhiteNoise serves collected static files. Persist and back up the database and
private media independently.

Production settings and manifest static collection have been checked locally.
A live PostgreSQL staging run, restricted Google Maps key, real-device checks,
and the controlled pilot remain the next validation tasks.
