# FloodRelief Connect: detailed project guide

Prepared on 2026-11-17 from the current implementation in this repository.
Canonical project reference: [floodrelief-proposal.pdf](floodrelief-proposal.pdf).

This guide explains what the project does, what each source folder and file is
responsible for, and how information moves between them. Start with sections
1-3, follow the example in section 8, and use the file tables when opening the
code. Paths in the tables are clickable and relative to this document.

The guide describes the implemented Django prototype. The
[project log](PROJECT_PROGRESS.md) records its development history and remaining
work; the [test report](TEST_REPORT.md) records what has actually been verified.

## Contents

1. [What the project does](#1-what-the-project-does)
2. [Technologies and their jobs](#2-technologies-and-their-jobs)
3. [How a browser request becomes a page](#3-how-a-browser-request-becomes-a-page)
4. [The folders at a glance](#4-the-folders-at-a-glance)
5. [Backend files explained](#5-backend-files-explained)
6. [Database records and relationships](#6-database-records-and-relationships)
7. [Pages and URLs](#7-pages-and-urls)
8. [A complete relief request through the code](#8-a-complete-relief-request-through-the-code)
9. [Frontend files and how they connect](#9-frontend-files-and-how-they-connect)
10. [Login, permissions and private information](#10-login-permissions-and-private-information)
11. [Notifications, maps and update polling](#11-notifications-maps-and-update-polling)
12. [Configuration, startup and migrations](#12-configuration-startup-and-migrations)
13. [Tests, demo data and project documents](#13-tests-demo-data-and-project-documents)
14. [Where to change what](#14-where-to-change-what)
15. [A practical reading and debugging path](#15-a-practical-reading-and-debugging-path)
16. [Glossary](#16-glossary)

## 1. What the project does

FloodRelief Connect keeps a flood-relief need in one record from submission to
confirmed receipt. A person submits a need; staff check it; a donor offers
support; a coordinator assigns that offer; the responder records delivery; the
recipient confirms that the support arrived.

Each request has two identifiers:

- A **UUID**: the database identity used in private request URLs.
- A **reference**, such as FRC-ABC-234: a short, readable code someone can quote
  over a phone. This is an illustrative reference, not a specific live record.

The lifecycle is:

~~~text
Received -> Verified -> Assigned -> In progress -> Delivered -> Closed
~~~

Every lifecycle change adds a timestamped **StatusEvent**. Reviews, support
pledges and deliveries also have their own records. The current status tells
you where the request is now; those records explain how it got there.

The four roles have different primary workspaces:

| Role | Main job | Main dashboard content |
| --- | --- | --- |
| Beneficiary, stored as `victim` | Request help and confirm receipt | Own requests, review responses, receipt prompts |
| Donor | Offer support and carry out assigned deliveries | Verified needs, personal pledges, assigned deliveries, approval state |
| NGO staff, stored as `ngo_staff` | Coordinate relief work | Review queue, requests ready for assignment, deliveries, operational metrics |
| Administrator, stored as `admin` | Oversee the platform and accounts | Account summaries, donor approvals, administration links, operations oversight |

NGO staff and administrators share coordination powers because both may need
to keep relief work moving. Account management additionally checks Django user
permissions. A role-focused menu presents the person's usual work; the server
still checks each action and record independently.

The main evaluation measure is **time to first meaningful staff action**. A
verification, rejection or request for more information can acknowledge a
request. The dashboard calculates the median of these durations and compares
them with the configurable two-hour target.

## 2. Technologies and their jobs

The dependency declarations are in [requirements.txt](../requirements.txt).
The recorded development environment uses Python 3.13 and Django 5.2.17; the
requirements allow compatible releases within the ranges below.

| Technology | Where it is used | What it contributes |
| --- | --- | --- |
| Python | [apps/](../apps/) and [config/](../config/) | Executes backend logic, validates actions, calculates metrics and accesses storage |
| Django, `>=5.2,<6.0` | Application framework | URL routing, views, forms, templates, ORM, sessions, password hashing, permissions, admin, migrations and testing |
| Django Template Language | [templates/](../templates/) | Combines HTML layouts with values supplied by Python views |
| HTML | Templates rendered into browser pages | Forms, links, headings, tables, native disclosures and accessible structure |
| CSS | [static/css/](../static/css/) | Existing palette and typography, page layouts, cards, spacing and responsive behavior |
| Plain JavaScript | [static/js/](../static/js/) | Menus, form feedback, motion, optional map loading and update notices |
| SQLite | [dev.py](../config/settings/dev.py) | Local development database stored in db.sqlite3 |
| PostgreSQL | [production.py](../config/settings/production.py) | Database selected by production settings; live staging remains planned |
| psycopg, `[binary]>=3.1,<4.0` | Production database connection | Python driver through which Django communicates with PostgreSQL |
| python-dotenv, `>=1.0,<2.0` | [base.py](../config/settings/base.py) | Loads local configuration values from .env |
| WhiteNoise, `>=6.6,<7.0` | Production middleware and static storage | Serves collected CSS, JavaScript and images with compression and hashed names |
| Gunicorn, `>=22.0,<24.0` on non-Windows systems | Production WSGI serving option | Runs the Django application behind the hosting setup |
| Google Maps JavaScript API | [map.js](../static/js/map.js) | Optional interactive map of approximate request areas |
| Google Fonts | [base.html](../templates/base.html) | Loads Fraunces, Archivo and JetBrains Mono; CSS also supplies fallback fonts |
| Git | .git and repository metadata files | Tracks source changes and project history |
| Node.js and Microsoft Edge | Local verification scripts under .local | Run browser checks and capture screenshots; these are development verification tools |
| Mermaid | Diagram blocks in this guide and [architecture.md](diagrams/architecture.md) | Describes architecture and relationships in readable Markdown diagrams |

The Python requirements file is the application's dependency list. The
frontend files are served directly; starting the Django application does not
require a frontend compilation step.

Several technologies are already part of Django rather than separate packages:

- **ORM**: translates Python model queries into database queries.
- **Authentication**: checks passwords and associates a request with a user.
- **Sessions**: remember a signed-in user across page requests.
- **Forms**: turn submitted text and files into validated values.
- **Admin**: generates authorized management screens from registered models.
- **Migrations**: record and apply changes to the database structure.

Python's standard library also matters: UUIDs identify records, Decimal stores
support quantities precisely, secrets generates reference characters, and
datetime/path utilities handle times and filenames.

## 3. How a browser request becomes a page

The project follows Django's **Model-Template-View** pattern:

| Part | Meaning here | Example |
| --- | --- | --- |
| Model | Defines stored information and related data behavior | ReliefRequest in apps/requests/models.py |
| Template | Defines the HTML sent to the browser | templates/requests/request_detail.html |
| View | Python code that handles a URL, checks access and prepares a response | request_detail() in apps/requests/views.py |
| Form | Validates submitted inputs before an action | ReviewForm in apps/verification/forms.py |
| Service | Performs a complete business operation | review_request() in apps/verification/services.py |

A service is this project's organization of business logic; it is an ordinary
Python function. Django does not require a services.py file. Here it keeps
workflow rules reusable by page views, administrator actions, tests and the
demo command.

All six app folders run inside one Django project and share its selected
database. A view calling a verification or delivery service makes a Python
function call inside that application.

~~~mermaid
flowchart TD
    Browser["Browser"]
    Middleware["Django middleware: session, user, CSRF"]
    URLs["config/urls.py and app urls.py"]
    View["View: access checks and response"]
    Form["Form: validated input"]
    Service["Service: workflow operation"]
    Models["Models and Django ORM"]
    DB[("Database")]
    Template["Template plus context values"]
    Assets["Static CSS, JavaScript and images"]
    Signals["Signals and after-commit notifications"]
    Browser --> Middleware --> URLs --> View
    View --> Form --> Service --> Models --> DB
    View --> Models
    Models --> Template
    View --> Template --> Browser
    Assets --> Browser
    Models -. saved records .-> Signals
    Signals -. after successful commit .-> DB
~~~

For a normal page visit:

1. The browser sends an HTTP **GET**, for example /requests/.
2. Django middleware attaches session/user information and applies shared
   request handling.
3. [config/urls.py](../config/urls.py) delegates the path to an app URL file.
4. That app's URL file selects a view.
5. The view queries models and prepares a **context** dictionary, such as a
   list of requests and their summary counts.
6. Django renders a template using that context.
7. The browser receives ordinary HTML and loads the linked CSS/JavaScript.

For a submitted form, the browser sends a **POST** with field values and,
when applicable, uploaded files. The view binds a Django form to that input.
Successful validation leads to a service call; a validation failure leads to
the same page with retained values and field errors.

After a successful action, the view usually redirects to a GET of the updated
page. This **POST-Redirect-GET** sequence gives the user an updated page and a
message without leaving the browser on the form submission response.

The browser does not receive executable Python or Django template tags.
For example, a template expression such as `{{ relief_request.reference }}`
has already become a reference string before the HTML reaches the browser.

## 4. The folders at a glance

~~~text
Floodrelief_connect/
|-- manage.py                 Command entry point
|-- requirements.txt          Python dependencies
|-- .env.example               Configuration example
|-- README.md                  Setup and demonstration instructions
|-- AGENTS.md                  Workspace continuation instructions
|-- config/                    Project settings and top-level routing
|   |-- settings/              Shared, development and production settings
|   |-- urls.py                Connects URL prefixes to apps
|   |-- wsgi.py / asgi.py       Server entry points
|-- apps/                      Backend feature modules
|   |-- users/                 Accounts, roles and donor approval
|   |-- requests/              Submission, lifecycle, public board and workbench
|   |-- verification/          Staff reviews and beneficiary responses
|   |-- donations/             Support pledges
|   |-- delivery/              Assignment, hand-over and recipient confirmation
|   |-- dashboard/             Role pages, metrics, inbox, maps and signals
|-- templates/                 HTML page layouts and reusable fragments
|-- static/                    Authored CSS, JavaScript and images
|-- docs/                      Proposal, guides, progress, validation and diagrams
|-- .venv/                     Installed local Python environment
|-- .local/                    Local verification data, reports and backups
|-- staticfiles/               Generated collectstatic output
|-- db.sqlite3                 Local working database
|-- .env                       Local environment values
|-- .git/                      Git's repository metadata
|-- __pycache__/               Generated Python bytecode
~~~

Uploads are stored under the configured **media/** directory when created.
Verification runs can override that directory to a location under .local.
The directory's existence depends on whether files have been stored there.

| Folder | Responsibility | How it connects |
| --- | --- | --- |
| [config/](../config/) | Makes the separate modules one Django project | Registers apps, chooses settings, installs middleware and connects URLs |
| [apps/](../apps/) | Implements feature and data behavior | Views use forms/services/models; modules refer to related records in other apps |
| [templates/](../templates/) | Produces the HTML structure | Views pass values to templates; templates include shared fragments and static assets |
| [static/](../static/) | Controls presentation and browser interactions | Template classes and data attributes connect to CSS rules and JS selectors |
| [docs/](./) | Explains requirements, implementation and validation | Helps developers understand, demonstrate and continue the project |
| .venv/ | Holds the Python interpreter and installed libraries | Its Python executable runs manage.py and imports Django |
| .local/ | Holds machine-local development/verification artifacts | Browser tests use isolated databases and media instead of the working data |
| staticfiles/ | Holds generated production static assets | collectstatic gathers files from static/ and Django's installed apps |
| media/ | Holds upload bytes | FileField values in the database point to files served through authorized views |
| .git/ | Holds source history and change tracking | Git uses it for status, diffs and commits |
| __pycache__/ | Holds automatically generated .pyc files | Python creates it while importing modules |

The authored implementation lives mainly in config, apps, templates and static.
Generated environments, databases and collected files are outputs of running
the project; their internal dependency/cache files do not define its features.

## 5. Backend files explained

### 5.1 Root and configuration files

| File | Job | Interaction |
| --- | --- | --- |
| [manage.py](../manage.py) | Starts Django command-line operations | Defaults to config.settings.dev and passes commands such as runserver, migrate and test to Django |
| [requirements.txt](../requirements.txt) | Declares dependency ranges | pip installs these into .venv |
| [.env.example](../.env.example) | Documents environment variables and example values | Serves as the starting point for local .env configuration |
| [config/settings/base.py](../config/settings/base.py) | Shared settings and environment parsing | Loads .env; defines installed apps, middleware, templates, auth model, paths and optional feature settings |
| [config/settings/dev.py](../config/settings/dev.py) | Local settings | Imports base settings, selects SQLite and configures development behavior |
| [config/settings/production.py](../config/settings/production.py) | Production settings | Selects PostgreSQL, WhiteNoise, static manifest storage and environment-driven security settings |
| [config/urls.py](../config/urls.py) | Main route list | Includes each app's URLs and Django admin; sets administration headings |
| [config/wsgi.py](../config/wsgi.py) | WSGI application entry point | Exposes application for a WSGI server such as Gunicorn |
| [config/asgi.py](../config/asgi.py) | ASGI application entry point | Exposes application for an ASGI-compatible server |
| [.gitignore](../.gitignore) | Excludes local/generated files from Git | Ignores environments, .env, databases, uploads, staticfiles, .local and caches |
| [.gitattributes](../.gitattributes) | Defines repository file handling | Normalizes text to LF line endings and marks images/PDFs/database/font files as binary |
| [AGENTS.md](../AGENTS.md) | Guides continuation work in this workspace | Requires proposal-based work, retained data, consecutive logs and relevant checks |

The local **.env** contains actual configuration values; **db.sqlite3** contains
the working data. Their contents are different from Python source code.

The **__init__.py** files in config, apps and their subdirectories mark Python
packages. They let imports such as `from apps.delivery.services import
assign_pledge` refer to this folder structure. The files under migrations,
management/commands and templatetags serve the same package purpose.

Each app also has an **apps.py** configuration class:

| File | Configuration job |
| --- | --- |
| [users/apps.py](../apps/users/apps.py) | Registers the users app and its metadata |
| [requests/apps.py](../apps/requests/apps.py) | Registers the relief-request app |
| [verification/apps.py](../apps/verification/apps.py) | Registers the verification app |
| [donations/apps.py](../apps/donations/apps.py) | Registers the donations app |
| [delivery/apps.py](../apps/delivery/apps.py) | Registers the delivery app |
| [dashboard/apps.py](../apps/dashboard/apps.py) | Registers the dashboard app; ready() imports signals to connect notification handlers |

When reading imports, `from .models import User` means “from models.py in this
same package.” An import beginning `from apps.requests.models import` refers
to the requests app. A model relationship written as `"requests.ReliefRequest"`
uses Django's app label and model name; Django resolves it through its model
registry.

### 5.2 apps/users: identity and account administration

| File | Job | Works with |
| --- | --- | --- |
| [models.py](../apps/users/models.py) | Role, custom User, UserManager and permission properties | Django auth, every actor-linked workflow record and role navigation |
| [forms.py](../apps/users/forms.py) | RegistrationForm, EmailAuthenticationForm and shared style_fields() | Registration/login pages; workflow forms also reuse the field styling helper |
| [views.py](../apps/users/views.py) | SignInView and register() | Validates account input, creates a permitted role account, signs the user in and redirects to the dashboard |
| [account_views.py](../apps/users/account_views.py) | Account summaries, filters, paginated oversight and approve_donor() | User permissions, account-management template and approval signals |
| [permissions.py](../apps/users/permissions.py) | coordinator_required and supporter_required decorators | Restricts the verification queue and verified-needs support page |
| [urls.py](../apps/users/urls.py) | Account routes | Mounted under /accounts/ by config/urls.py |
| [admin.py](../apps/users/admin.py) | Django user/role management | Custom add/edit forms, support approval, staff/superuser flags, groups and permissions |
| [tests.py](../apps/users/tests.py) | Account/authentication tests | Detailed coverage is listed in section 13 |
| [test_account_management.py](../apps/users/test_account_management.py) | Native oversight/approval tests | Checks user-management permissions and preservation of account state |

User extends Django's **AbstractBaseUser** and **PermissionsMixin**.
AbstractBaseUser supplies password and login machinery; PermissionsMixin
supplies superuser/group/permission behavior.

The login identifier is **email**, defined by `USERNAME_FIELD = "email"`.
Django's authentication form still calls its input field username internally;
EmailAuthenticationForm makes that input an email field. It also resolves
case-insensitive email matches, including accounts created through admin.

The permission properties answer different questions:

- **can_coordinate**: can an active NGO staff, administrator or superuser
  perform relief coordination?
- **can_support**: can an active approved donor or coordinator offer support?
- **can_view_accounts**: is the active account also is_staff and permitted to
  view or change Django User records?
- **can_approve_donors**: is the active staff account permitted to change Users?
- **workspace_role**: which role should the dashboard present? Superusers
  receive the administrator workspace.

Public registration offers beneficiary and donor roles. New donors start with
support_approved false. Staff roles and management privileges are administered
through authorized account administration.

### 5.3 apps/requests: the central request and workbench

| File | Job | Works with |
| --- | --- | --- |
| [models.py](../apps/requests/models.py) | ReliefRequest, StatusEvent, lifecycle choices, reference generation, transitions and acknowledgement metrics | All workflow services; dashboards; public and private request pages |
| [forms.py](../apps/requests/forms.py) | ReliefRequestForm and phone validation | Public submission page and shared account phone validation |
| [views.py](../apps/requests/views.py) | Submission, public board, private detail/actions, evidence download and JSON update snapshots | Request forms/templates plus verification, donation and delivery services |
| [permissions.py](../apps/requests/permissions.py) | can_view_request() | Private request view, private snapshots and the template's Open request link |
| [files.py](../apps/requests/files.py) | Randomized storage paths and upload checks | Request evidence, review evidence and delivery proof |
| [urls.py](../apps/requests/urls.py) | Submission, board, detail, evidence and update routes | Mounted under /requests/ |
| [admin.py](../apps/requests/admin.py) | Request oversight and retained event display | Shows metrics, private evidence links and a service-based authorized verification action |
| [templatetags/request_extras.py](../apps/requests/templatetags/request_extras.py) | can_open, minutes and iso template filters | Reuses access checks and formats durations/timestamps for HTML |
| [management/commands/seed_demo.py](../apps/requests/management/commands/seed_demo.py) | Creates fictional demonstration accounts/requests | Calls the same workflow services and backdates demo records |

Three view responsibilities are especially useful to recognize:

1. **RequestCreateView** accepts a new request. Its form_valid() associates a
   signed-in user, preserves evidence metadata and calls ReliefRequest.save().
2. **RequestListView** reads and filters public board records. It paginates 12
   requests and supplies status counts and acknowledgement statistics.
3. **request_detail()** is the shared authorized workbench. It chooses the
   submitted action, validates the relevant form and calls the appropriate
   feature service.

The request-detail forms use an **action** field with values review, respond,
pledge, assign, start, deliver or confirm. The view binds only the submitted
form to POST/files. Generated field IDs distinguish the forms on the same page.
The **start** action has no additional input form; it still has role/stage
checks in the view and delivery service.

ReliefRequest.save() creates a request at Received, generates its reference
when needed and creates the first StatusEvent inside a database transaction.
Ordinary save() rejects direct status changes to an existing request.

**generate_reference()** constructs the short FRC-XXX-XXX tracking code from
six randomly selected characters, excluding easily confused 0/O/1/I characters,
and checks for an existing reference before returning it.

**transition_to()** is the common lifecycle write operation. It reloads and
locks the current request, checks the next allowed stage, writes an event,
updates the status/timestamps and commits those changes together.
**validate_transition()** checks both actor permission and required supporting
records. **acknowledge()** records first staff action even when the request
remains at Received.

### 5.4 apps/verification: checking a need

| File | Job | Works with |
| --- | --- | --- |
| [models.py](../apps/verification/models.py) | Verification record, decisions, methods, notes and optional evidence | Related to a request and the user who recorded the review/response |
| [forms.py](../apps/verification/forms.py) | ReviewForm and ReviewResponseForm | Workbench review/response panels, including the hidden review revision |
| [services.py](../apps/verification/services.py) | review_request() and respond_to_review() | Creates retained review records, acknowledges the request and advances verified requests |
| [views.py](../apps/verification/views.py) | Staff review queue and private review-evidence download | Request models, coordinator permissions and queue template |
| [urls.py](../apps/verification/urls.py) | Queue and evidence routes | Mounted under /verification/ |
| [admin.py](../apps/verification/admin.py) | Read-only review administration and shared RecordAdmin class | Other retained-record admin classes reuse RecordAdmin |

A review decision is separate from a lifecycle status:

- **verified** adds a Verification and moves Received to Verified.
- **rejected** adds a Verification and acknowledges first staff action while
  the lifecycle remains Received.
- **more_info** adds a Verification and allows the requester to respond.
- A requester response adds a new **pending** Verification with method
  requester. This returns it to the staff review queue.

Previous decisions remain in history. The latest Verification determines the
current review state. A hidden revision containing the latest review ID helps
detect a staff submission made after someone else recorded a review/response.

### 5.5 apps/donations: recording support offers

| File | Job | Works with |
| --- | --- | --- |
| [models.py](../apps/donations/models.py) | Donation record: donor, request, support type, quantity, unit and offer status | Delivery links to the selected Donation |
| [forms.py](../apps/donations/forms.py) | DonationForm | Validates the support description and INR funds unit |
| [services.py](../apps/donations/services.py) | pledge_support() and withdraw_pledge() | Checks approval, request stage and pledge ownership/state |
| [views.py](../apps/donations/views.py) | Verified-needs discovery and POST-only withdrawal | Supporter permissions, request summaries and pledge services |
| [urls.py](../apps/donations/urls.py) | Discovery and withdrawal routes | Mounted under /support/ |
| [admin.py](../apps/donations/admin.py) | Read-only pledge history | Uses RecordAdmin from verification/admin.py |

In this project a Donation is a **pledge**: an offer of goods, transport or
funds. A funds offer uses INR as its unit and Decimal for its amount. Payment
collection is outside the implemented pledge workflow.

Pledges can be made while the request is Verified and awaiting assignment.
The donor can withdraw an unassigned Offered pledge. Assignment and hand-over
change the selected pledge's status to Assigned and Delivered.

### 5.6 apps/delivery: assigning and completing support

| File | Job | Works with |
| --- | --- | --- |
| [models.py](../apps/delivery/models.py) | Delivery record: selected pledge, responder, assigning user, timestamps, proof and receipt confirmation | One request and one Donation; references several User actors |
| [forms.py](../apps/delivery/forms.py) | AssignmentForm, PledgeChoiceField, DeliveryConfirmationForm and ReceiptConfirmationForm | Workbench assignment, hand-over and receipt panels |
| [services.py](../apps/delivery/services.py) | assign_pledge(), start_delivery(), confirm_delivery() and confirm_receipt() | Request transitions and selected pledge status updates |
| [views.py](../apps/delivery/views.py) | Private proof download | Checks requester, assigned responder or coordinator access |
| [urls.py](../apps/delivery/urls.py) | Delivery-proof route | Mounted under /delivery/ |
| [admin.py](../apps/delivery/admin.py) | Read-only delivery/confirmation history | Reuses RecordAdmin |

Delivery action buttons submit to the request workbench. The delivery URL file
itself exposes the proof download; its services do the assignment/delivery
business work.

The selected Donation determines the responder. Assignment rechecks that the
offer is still available and its donor still has support approval. A request
has one lead Delivery record in the implemented prototype.

Hand-over and final receipt are separate:

- **confirm_delivery()** records the recipient, hand-over notes, delivery time
  and optional proof; it moves the request to Delivered.
- **confirm_receipt()** records the requester's confirmation, or a coordinator's
  recorded phone/in-person confirmation, before moving it to Closed.

### 5.7 apps/dashboard: pages and supporting visibility

| File | Job | Works with |
| --- | --- | --- |
| [views.py](../apps/dashboard/views.py) | LandingView, role home(), activity(), inbox and read actions | Queries request, pledge, delivery, review, account and notification records |
| [models.py](../apps/dashboard/models.py) | Persistent Notification records | Recipient-owned inbox and unread counts |
| [maps.py](../apps/dashboard/maps.py) | request_map() and safe public area data | Request models, map template and optional browser map enhancement |
| [notifications.py](../apps/dashboard/notifications.py) | coordinator_ids() and notify_after_commit() | Finds active recipients and creates notifications after a successful commit |
| [signals.py](../apps/dashboard/signals.py) | Reacts to saved status events, reviews, pledges and support-approval changes | Connects workflow/account writes to notification creation |
| [context_processors.py](../apps/dashboard/context_processors.py) | Shared unread_notification_count and acknowledgement target values | Makes these values available to rendered pages through template settings |
| [urls.py](../apps/dashboard/urls.py) | Landing, map, dashboard, activity and inbox routes | Included at the root path in config/urls.py |
| [admin.py](../apps/dashboard/admin.py) | Read-only Notification inspection | Reuses RecordAdmin |
| [tests.py](../apps/dashboard/tests.py) | Visibility, notification, role and privacy tests | Uses workflow fixtures and checks the supporting features |

The home() view prepares the role's headings, actions, counts and record
previews. It passes **workspace_role** to
[dashboard/home.html](../templates/dashboard/home.html), which includes one
of four role templates.

Activity is the full paginated history. Beneficiaries start on personal
requests, donors on personal pledges, and coordinators on all operations.
The dashboard's request preview contains six recent requests; activity is how
the user reaches older records.

## 6. Database records and relationships

A **model instance** is one Python object representing a database row.
A **ForeignKey** stores a link to another row; a **OneToOneField** makes that
link unique. Separate apps share the configured database and connect their
records through these relationships.

| Model | Default table | Information it stores |
| --- | --- | --- |
| Role | users_role | One of the four role names and a description |
| User | users_user | Name, email, phone, password hash, role and account/permission flags |
| ReliefRequest | requests_reliefrequest | Need, scale, urgency, public/private location, optional evidence and lifecycle state |
| StatusEvent | requests_statusevent | Previous/new stage, actor, timestamp and event note |
| Verification | verification_verification | Review or requester response, decision, method, notes and optional evidence |
| Donation | donations_donation | Support offer, donor, amount/quantity, unit and pledge status |
| Delivery | delivery_delivery | Assigned offer/responder, hand-over and recipient confirmation |
| Notification | dashboard_notification | Recipient, event key, message, related request, created/read times |

Django also creates framework tables for sessions, content types, groups,
permissions and applied migrations. These support authentication and management
without needing equivalent application model files.

~~~mermaid
erDiagram
    ROLE o|--o{ USER : role
    USER o|--o{ RELIEF_REQUEST : submits
    RELIEF_REQUEST ||--|{ STATUS_EVENT : records
    USER o|--o{ STATUS_EVENT : acts
    RELIEF_REQUEST ||--o{ VERIFICATION : reviews
    USER ||--o{ VERIFICATION : records_review
    RELIEF_REQUEST ||--o{ DONATION : offers
    USER ||--o{ DONATION : pledges
    RELIEF_REQUEST ||--o| DELIVERY : lead_delivery
    DONATION ||--o| DELIVERY : assigned_offer
    USER ||--o{ DELIVERY : responds
    USER ||--o{ NOTIFICATION : receives
    RELIEF_REQUEST o|--o{ NOTIFICATION : concerns
~~~

Read this diagram as:

- One role can belong to many users; a user's role can be empty.
- A user can submit many requests. Anonymous requests have no submitted_by user.
- A request has an initial event and an event for each later lifecycle change.
- A request can have multiple retained reviews and multiple support offers.
- A request can have one lead delivery, linked to one selected offer.
- A delivery also records assigned_by and, later, confirmed_by users.
- A notification belongs to one user. Account-approval notifications can have
  no related request.

The model **related_name** values make reverse lookups readable. For example:

~~~python
user.relief_requests.all()        # Requests this user submitted
relief_request.events.all()       # The request's lifecycle history
relief_request.verifications.all() # Its review/response history
relief_request.donations.all()     # Its support offers
relief_request.delivery           # Its single lead delivery, if assigned
user.notifications.all()          # This user's inbox records
~~~

For regular selection, a view uses the ORM:

~~~python
ReliefRequest.objects.filter(status=RequestStatus.VERIFIED)
~~~

Django builds the database query from that expression. **select_related()**
fetches linked single records using joins; **prefetch_related()** fetches
collections of related records in additional grouped queries. The board and
workbench use these to reduce repeated queries while rendering cards/history.

Deletion behavior is also declared in the models. SET_NULL preserves a record
when an optional submitting/acting user is removed. PROTECT retains users
referenced by review, pledge and delivery history. CASCADE connects dependent
rows to their parent request. The application's retained-record admin disables
manual addition, editing and deletion of audit/workflow history.

### Transactions and ordered status changes

A database **transaction** groups changes into one successful unit. For
example, assignment must create a Delivery, update the chosen Donation and
advance the ReliefRequest together. The service wraps these writes in
transaction.atomic; an error rolls the database changes back.

Services use **select_for_update()** to lock the current rows on a supporting
database. PostgreSQL supports these row locks. SQLite has different locking
behavior and does not provide equivalent SELECT FOR UPDATE row locks; the
planned PostgreSQL staging checks cover concurrent review/assignment behavior.

The stages' main timestamps are stored in the appropriate records:

| Stage/action | Relevant timestamp records |
| --- | --- |
| Received | ReliefRequest.submitted_at and the initial StatusEvent.changed_at |
| First staff action | ReliefRequest.acknowledged_at; first Verification.reviewed_at |
| Verified | Verification.reviewed_at and a StatusEvent.changed_at |
| Assigned | Delivery.assigned_at and a StatusEvent.changed_at |
| In progress | Delivery.started_at and a StatusEvent.changed_at |
| Delivered | Delivery.delivered_at and a StatusEvent.changed_at |
| Closed | Delivery.recipient_confirmed_at, ReliefRequest.closed_at and a StatusEvent.changed_at |

The event history supplies the timeline for every stage; the request model
does not need a separate field for every stage timestamp.

## 7. Pages and URLs

The root URL configuration adds a prefix; the app URL file supplies the rest.
For example, root **accounts/** plus users **manage/** produces
**/accounts/manage/**.

The placeholders below indicate UUIDs. Request detail/evidence/update URLs use
a Request UUID; review evidence uses a Verification UUID; pledge withdrawal
uses a Donation UUID; delivery proof uses a Delivery UUID.

| URL | Normal use | View and result |
| --- | --- | --- |
| / | GET | dashboard.LandingView renders the public landing page and real aggregate metrics |
| /accounts/register/ | GET / POST | users.register renders/validates registration and signs in a new permitted account |
| /accounts/login/ | GET / POST | users.SignInView handles email/password authentication |
| /accounts/logout/ | POST | Django LogoutView ends the session and redirects to the landing page |
| /accounts/manage/ | GET | users.account_views.manage_accounts renders the authorized account list |
| /accounts/manage/&lt;user-id&gt;/approve/ | POST | users.account_views.approve_donor changes active donor support approval |
| /dashboard/ | GET | dashboard.home renders the correct role workspace |
| /dashboard/activity/ | GET | dashboard.activity renders filtered/paginated records |
| /dashboard/notifications/ | GET | dashboard.notifications renders the private inbox |
| /dashboard/notifications/read-all/ | POST | dashboard.mark_all_notifications_read marks the owner's unread items |
| /dashboard/notifications/&lt;notification-id&gt;/read/ | POST | dashboard.mark_notification_read marks one owned item |
| /requests/new/ | GET / POST | requests.RequestCreateView renders/validates a submission |
| /requests/ | GET | requests.RequestListView renders the public board |
| /requests/updates/ | GET | requests.board_updates returns a public revision indicator as JSON |
| /requests/&lt;request-id&gt;/ | GET / POST | requests.request_detail renders the workbench or handles a workflow action |
| /requests/&lt;request-id&gt;/evidence/ | Download | requests.supporting_evidence returns an authorized attachment |
| /requests/&lt;request-id&gt;/updates/ | GET | requests.request_updates returns an authorized status/revision snapshot |
| /verification/ | GET | verification.queue renders received requests filtered by review state |
| /verification/&lt;review-id&gt;/evidence/ | Download | verification.evidence returns an authorized review attachment |
| /support/ | GET | donations.available renders verified requests awaiting support |
| /support/&lt;pledge-id&gt;/withdraw/ | POST | donations.withdraw calls the pledge withdrawal service |
| /delivery/&lt;delivery-id&gt;/proof/ | Download | delivery.proof returns authorized hand-over proof |
| /map/ | GET | dashboard.maps.request_map renders approximate areas and optional map data |
| /admin/ | Authorized management | Django admin provides registered model screens |

Download links normally use GET. Mutating account/inbox/withdrawal endpoints
are explicitly POST-only, and Django's CSRF middleware protects form requests.

Query parameters select a view without changing records. Examples:

~~~text
/requests/?status=verified&urgency=high&q=Barpeta
/dashboard/activity/?kind=deliveries&scope=all
/dashboard/activity/?kind=requests&status=delivered
/accounts/manage/?status=pending
/verification/?decision=more_info
/map/?category=food_water
~~~

Changing scope in a URL does not grant access to another user's records.
Activity only enables all-operations scope for a coordinator.

## 8. A complete relief request through the code

Consider an illustrative need for 24 drinking-water/food kits. The following
steps explain normal behavior; the specific example is not a new database
record created by this guide.

### 8.1 Beneficiary submits the need

The beneficiary opens /requests/new/.
[request_form.html](../templates/requests/request_form.html) presents seven
required fields: contact name, phone, category, urgency, people affected,
location and description. Optional public area, coordinates and evidence are
grouped in a native disclosure.

On POST, **RequestCreateView** passes input to **ReliefRequestForm**.
The form checks a reachable phone format, meaningful text, people between
1 and 5000, and a description between 15 and 1200 characters. Model/form
validation also checks coordinate ranges/pairs and uploaded evidence.

The view assigns submitted_by for a signed-in user and calls save().
The model writes the request/reference and its Received event atomically.
A signed-in user is redirected to the private workbench. An anonymous
submission is redirected to the public board with a highlight reference to
the new card.

### 8.2 Staff reviews the need

Staff opens /verification/. **queue()** selects Received requests according to
their latest review decision and prioritizes urgency, then submission age.
Opening a request leads to the shared workbench.

The review panel posts **action=review**. **request_detail()** checks
can_coordinate, validates **ReviewForm** and calls **review_request()**.
The service checks the current request stage, review revision, decision,
method and notes, then creates a Verification.

It calls **acknowledge()** using the review time. For a verified decision it
also calls **transition_to(Verified)**, adding a lifecycle event. That saved
event leads to a notification scheduled after commit.

If staff ask for more information, the request remains Received. The owner
posts **action=respond**; **respond_to_review()** appends a pending review
record and the queue can present it for a fresh staff decision.

### 8.3 Approved donor offers support

The donor opens /support/. **available()** lists Verified requests. Donor
discovery displays/searches public areas before assignment.

The workbench pledge panel posts **action=pledge**.
**DonationForm** validates the description, amount and unit.
**pledge_support()** rechecks support approval and the request's Verified
stage, then creates a Donation with status Offered.

The request remains Verified: an available offer still needs a coordinator's
assignment. Saving the offer also updates the request's revision and schedules
notifications for the relevant beneficiary/coordinators.

### 8.4 Coordinator assigns the offer

The coordinator submits **action=assign** from the same request page.
**AssignmentForm** presents unassigned offers attached to that request.
**assign_pledge()** rechecks the chosen offer and donor, creates one Delivery,
sets its responder to the donor and marks the offer Assigned.

The service advances the request to Assigned through transition_to().
The new event records the actor/time, and the responder receives the relevant
after-commit update.

### 8.5 Responder starts and records hand-over

The responder submits **action=start**. **start_delivery()** checks that this
is the assigned responder or a coordinator, records started_at and advances
the request to In progress.

After hand-over, **action=deliver** carries the recipient name, confirmation
note and optional proof. **DeliveryConfirmationForm** validates those fields.
**confirm_delivery()** records the delivery, marks the pledge Delivered and
advances the request to Delivered.

The request is now waiting for the final recipient confirmation.

### 8.6 Beneficiary confirms receipt

The beneficiary selects **Confirm receipt** on an owned delivered request.
The panel submits **action=confirm**, including a confirmation checkbox and
notes. **confirm_receipt()** checks owner/coordinator permission and the
Delivered stage.

It saves recipient_confirmed_at, confirmed_by and confirmation notes, then
advances the request to Closed. The closure has its own event and timestamp.
For a phone/anonymous entry, staff can record the recipient's confirmation.

~~~mermaid
sequenceDiagram
    actor B as Beneficiary
    actor S as Coordinator
    actor D as Donor or responder
    participant V as Request views
    participant F as Feature services
    participant M as Models and database
    participant N as After-commit inbox
    B->>V: Submit valid need
    V->>M: Save request plus Received event
    S->>V: action=review
    V->>F: review_request()
    F->>M: Review, acknowledgement, Verified event
    M-->>N: Saved event notification
    D->>V: action=pledge
    V->>F: pledge_support()
    F->>M: Offered Donation
    S->>V: action=assign
    V->>F: assign_pledge()
    F->>M: Delivery, Assigned Donation, Assigned event
    D->>V: action=start
    V->>F: start_delivery()
    F->>M: Start time and In progress event
    D->>V: action=deliver
    V->>F: confirm_delivery()
    F->>M: Hand-over, proof, Delivered event
    B->>V: action=confirm
    V->>F: confirm_receipt()
    F->>M: Receipt confirmation and Closed event
    M-->>N: Relevant committed updates
~~~

### 8.7 Action-to-file reference

All seven action values below are handled by request_detail() in
[requests/views.py](../apps/requests/views.py).

| Submitted action | Input form | Service | Main data result |
| --- | --- | --- | --- |
| review | ReviewForm | verification.services.review_request | New review and first acknowledgement; Verified event when accepted |
| respond | ReviewResponseForm | verification.services.respond_to_review | New pending review response |
| pledge | DonationForm | donations.services.pledge_support | New Offered pledge |
| assign | AssignmentForm | delivery.services.assign_pledge | Selected pledge and lead Delivery; Assigned event |
| start | Permission/stage checks; no extra fields | delivery.services.start_delivery | started_at and In progress event |
| deliver | DeliveryConfirmationForm | delivery.services.confirm_delivery | Hand-over/proof, delivered pledge and Delivered event |
| confirm | ReceiptConfirmationForm | delivery.services.confirm_receipt | Recipient confirmation and Closed event |

## 9. Frontend files and how they connect

### 9.1 Template inheritance and page files

[base.html](../templates/base.html) supplies the HTML document, common fonts,
base styles, header, messages, footer and shared scripts.
[workspace_base.html](../templates/workspace_base.html) extends it with account
styles, the authenticated sidebar/mobile menu, a workspace content area and
the compact workspace footer.

~~~text
base.html
|-- public landing, submission and board pages
|-- workspace_base.html
    |-- login / registration / account management
    |-- role dashboards / activity / notifications / map
    |-- private request workbench / support discovery / review queue
~~~

**extends** chooses the parent layout; **block** supplies a page's section;
**include** reuses a fragment. A page inherits the common document rather than
copying the header and CSS links into every template.

| Template | Page/content responsibility | Main data provider |
| --- | --- | --- |
| [dashboard/landing.html](../templates/dashboard/landing.html) | Public introduction, lifecycle, role links, request preview and metrics | LandingView |
| [dashboard/home.html](../templates/dashboard/home.html) | Common dashboard heading/actions/metrics and role-template selection | home() |
| [dashboard/roles/beneficiary.html](../templates/dashboard/roles/beneficiary.html) | Own request cards and requester guidance | Beneficiary branch of home() |
| [dashboard/roles/donor.html](../templates/dashboard/roles/donor.html) | Approval state, available needs, personal support and deliveries | Donor branch of home() |
| [dashboard/roles/ngo_staff.html](../templates/dashboard/roles/ngo_staff.html) | Review, assignment and delivery coordination | NGO branch of home() |
| [dashboard/roles/admin.html](../templates/dashboard/roles/admin.html) | Donor approvals, account tools and operations overview | Administrator branch of home() |
| [dashboard/activity.html](../templates/dashboard/activity.html) | Record-type/ownership filters and full paginated history | activity() |
| [dashboard/notifications.html](../templates/dashboard/notifications.html) | Inbox, unread filter and read actions | notifications() |
| [dashboard/map.html](../templates/dashboard/map.html) | Public area list, map controls and safe JSON data | request_map() |
| [requests/request_form.html](../templates/requests/request_form.html) | Submission fields, optional details and validation feedback | RequestCreateView |
| [requests/request_list.html](../templates/requests/request_list.html) | Public board, filters, request cards and pagination | RequestListView |
| [requests/request_detail.html](../templates/requests/request_detail.html) | Private/public-safe detail, history and permitted workflow panels | request_detail() |
| [users/login.html](../templates/users/login.html) | Email/password sign-in form | SignInView |
| [users/register.html](../templates/users/register.html) | Permitted account registration | register() |
| [users/manage_accounts.html](../templates/users/manage_accounts.html) | Account summaries, search/filters and authorized approval controls | manage_accounts() |
| [verification/queue.html](../templates/verification/queue.html) | Staff review filters and prioritized request cards | queue() |
| [donations/available.html](../templates/donations/available.html) | Verified needs awaiting support | available() |

Templates use context values rather than implementing workflow writes. For
example, can_review controls whether the workbench displays a review panel.
The view and service also enforce that permission when a POST arrives.

### 9.2 Reusable partial templates

These files reduce repeated HTML and keep shared controls consistent.

| Partial | Responsibility | Used by |
| --- | --- | --- |
| [header.html](../templates/partials/header.html) | Common wave branding, desktop links and native mobile menu | base.html |
| [header_action.html](../templates/partials/header_action.html) | Chooses the main header action for the user's role/approval | header.html |
| [footer.html](../templates/partials/footer.html) | Full public footer and project links | Public page layout |
| [workspace_footer.html](../templates/partials/workspace_footer.html) | Compact workspace footer | workspace_base.html |
| [workspace_nav.html](../templates/partials/workspace_nav.html) | Role links, current page, unread count and sign-out form | Signed-in workspace pages |
| [workspace_pagination.html](../templates/partials/workspace_pagination.html) | Previous/next controls preserving active queries | Activity, inbox, support, review and account lists |
| [messages.html](../templates/partials/messages.html) | Django success/error messages and optional dismissal | base.html |
| [icon.html](../templates/partials/icon.html) | Shared inline SVG icon shapes | Navigation, cards, forms and actions |
| [field.html](../templates/partials/field.html) | Label, input, required/optional marker, help, errors and password toggle | Account and workflow forms |
| [form_errors.html](../templates/partials/form_errors.html) | Form-wide errors and linked error summary | Submission/account/action forms |
| [action_form.html](../templates/partials/action_form.html) | POST form, CSRF token, hidden action and upload encoding | Workbench workflow panels |
| [status_badge.html](../templates/partials/status_badge.html) | Current-stage badge | Request cards, workbench, deliveries and activity |
| [tracker.html](../templates/partials/tracker.html) | Six ordered lifecycle steps and recorded timestamps | Public cards and workbench |
| [request_card.html](../templates/partials/request_card.html) | Public-safe board card, metric and event trail | Public board |
| [request_summary.html](../templates/partials/request_summary.html) | Compact workspace request card and next-step link | Dashboards, support, review and request activity |
| [delivery_card.html](../templates/partials/delivery_card.html) | Assigned delivery card and action link | Authorized dashboard delivery sections |
| [dashboard_metrics.html](../templates/partials/dashboard_metrics.html) | Role-specific count/value/link cells | home.html |
| [operations_summary.html](../templates/partials/operations_summary.html) | Acknowledgement, confirmation coverage and stage summaries | NGO/administrator role templates |
| [update_notice.html](../templates/partials/update_notice.html) | Initially hidden status-watch message and refresh button | Public board and private request workbench |

Public request_card shows public_area and neutral actor labels. Workspace
request_summary shows private location to its owner/coordinators and public
area to other viewers. delivery_card is populated with deliveries scoped to
the responder or coordinator.

### 9.3 CSS responsibilities

| CSS file | Main job |
| --- | --- |
| [base.css](../static/css/base.css) | Shared theme tokens, resets, typography, buttons, masthead, messages, public footer, status colors and motion/accessibility rules |
| [components.css](../static/css/components.css) | Status badges, lifecycle tracker, audit trail, relative-time styling and update notices |
| [landing.css](../static/css/landing.css) | Hero imagery, introduction sections, lifecycle rail, statistics and aligned role cards |
| [form.css](../static/css/form.css) | Submission layout, shared fields, radios, errors, optional details and submit feedback |
| [board.css](../static/css/board.css) | Public-board metrics, filters, request cards, card alignment and pagination |
| [workspace.css](../static/css/workspace.css) | Role/sidebar layout, account pages, workspace cards, metrics, toolbars, forms, responsive account table and compact footer |

The **:root** variables in base.css are the common theme values. Other CSS
files use them through expressions such as `var(--sand)` and
`var(--current)`. This connects the original water/sand/amber palette across
pages. Fraunces is the display typeface, Archivo the body typeface and JetBrains
Mono the data/reference/timestamp typeface.

For alignment, workspace grids stretch cards to consistent heights on wider
layouts, and flexible card interiors push action footers into alignment.
Metric cells use CSS **subgrid** so their labels, values and helper links share
row tracks. Filter inputs/buttons have consistent heights. Media queries
collapse layouts for smaller viewports, and a container query adapts account
records to the available table width, including width reduced by a sidebar.

### 9.4 JavaScript responsibilities

| JavaScript file | Behavior | Main HTML connection |
| --- | --- | --- |
| [motion.js](../static/js/motion.js) | Scroll reveals, masthead state, count animation, tracker activation and relative timestamps | data-reveal, data-count, data-tracker and time[data-relative] |
| [ui.js](../static/js/ui.js) | Menu closing/focus, desktop/mobile workspace navigation, password visibility, error focus and message dismissal | data-menu, data-workspace-nav, data-password-toggle and error/message controls |
| [form.js](../static/js/form.js) | Description counter, immediate field feedback, submission wait state and duplicate-click suppression | data-reqform, data-counter and data-submit |
| [board.js](../static/js/board.js) | Highlights a newly submitted card, tidies the highlight query and enhances selected filter changes | data-board and public filter controls |
| [updates.js](../static/js/updates.js) | Checks revisions and reveals a refresh notice when activity changes | data-status-watch, data-update-url and data-revision |
| [map.js](../static/js/map.js) | Loads Google Maps on request and creates approximate-area markers/fallback feedback | data-relief-map, map JSON and the load-map button |

motion.js and ui.js are loaded by the common base layout. Individual page
templates add form.js, board.js, updates.js or map.js when needed.

The external script tags use **defer**, so the browser runs those scripts after
parsing the HTML. Their selectors can then find the controls already on the page.

The connecting mechanism is visible in HTML:

~~~html
<div class="workspace-grid">...</div>
<div data-status-watch data-update-url="..." data-revision="..." hidden>...</div>
~~~

- The **class** connects the element to CSS layout rules.
- The **data attributes** give JavaScript a way to find the element and read
  page-specific configuration.
- The **context values** that fill those attributes come from Django views.

JavaScript improves the page's interaction. Django forms and services remain
the authority for valid inputs and authorized workflow changes. Native
details/summary controls and ordinary form posts keep core tasks usable when
enhancements are unavailable.

### 9.5 Images and the existing theme

| Asset | Purpose |
| --- | --- |
| [hero-flood.jpg](../static/images/hero-flood.jpg) | Landing hero photography |
| [lifecycle-band.jpg](../static/images/lifecycle-band.jpg) | Lifecycle-section photography |
| [closing-relief.jpg](../static/images/closing-relief.jpg) | Closing-section photography |
| [favicon.svg](../static/images/favicon.svg) | Browser icon based on the wave identity |
| [CREDITS.md](../static/images/CREDITS.md) | Image credits and licensing references |

The main wave logo and interface icons are SVG markup in the shared templates.
CSS combines photographs with colored overlays and supplies the grain texture.
The recent UI refinements retain these theme assets and type/palette definitions.

## 10. Login, permissions and private information

### 10.1 How login stays attached to later requests

1. The login form posts an email and password.
2. Django authentication checks the stored password hash.
3. Django records the authenticated identity in a session.
4. The browser sends its session cookie on later requests.
5. SessionMiddleware reads the session and AuthenticationMiddleware exposes
   the user as **request.user**.
6. Views, permission helpers and templates use that user to select access and
   workspace content.

Passwords are stored as hashes through Django's password tooling. The
demonstration password is a value supplied to that tooling; it is not stored
as the User record's plaintext password.

The **is_staff** flag concerns access to Django's administration site.
The NGO role concerns relief coordination. These are separate checks: an NGO
role does not automatically grant User management permissions.

### 10.2 Access checks occur in several places

| Location | What it checks |
| --- | --- |
| login_required | The page/action has an authenticated user |
| coordinator_required / supporter_required | Access to a role/approval-restricted feature page |
| can_view_request() | Access to a specific private request record |
| request_detail() action map | Whether the user may submit this kind of operation |
| Workflow services | Current role/ownership/approval, current stage and supporting records |
| Model transition validation | Ordered next stage, authorized actor and required review/delivery/confirmation |
| Templates | Which controls and information to present for the authorized context |

The template's hidden button is presentation, while the view/service checks
enforce the action. This matters if someone submits a URL/form independently
of the visible interface.

The private request access helper permits active authenticated coordinators,
the request owner, approved supporters while it is Verified, and users with a
pledge associated with the request. The workbench separately limits private
details and other donors' offers.

### 10.3 Public and private data

| Surface | Data exposed |
| --- | --- |
| Public landing/board cards | Reference, category, public area, urgency, people affected, status and timestamps |
| Public board event trail | Stage changes/times with neutral requester/relief-team/system labels |
| Public area map/list | Public fields and coordinates rounded to two decimal places |
| Request owner/coordinator workbench | Authorized private description, location/contact details and review history |
| Assigned responder workbench | Delivery-relevant private contact/location details |
| Request/review evidence routes | Request owner and authorized coordinators |
| Delivery proof route | Request owner, assigned responder and authorized coordinators |
| Account management/inbox | User-management-authorized accounts or the inbox's own recipient, respectively |

Public search matches reference, public area and category. Private descriptions,
exact addresses, contact details, review notes and file metadata stay out of
public cards/search/map serialization.

Duplicate suggestions are a staff workbench query for other open requests with
the same category and matching location. They are suggestions for a reviewer;
the service does not automatically reject requests because of a match.

### 10.4 How uploaded files work

An upload has two parts: **bytes on disk** and **metadata/path in the database**.

1. The HTML form uses multipart/form-data.
2. Django receives files in request.FILES.
3. files.py checks a 5 MB limit, JPEG/PNG/PDF extension and the corresponding
   initial file signature.
4. evidence_path() creates a randomized filename under evidence/.
5. Django's file storage writes the bytes under MEDIA_ROOT, and the model stores
   the file path plus original-name metadata where applicable.
6. An authorized download view opens the file and returns FileResponse with
   attachment disposition.

MEDIA_URL is a configuration value, but config/urls.py does not publish a
public /media/ directory. The download views decide who can receive each file.
Evidence ownership checks are different from general verified-request viewing.

### 10.5 CSRF and account approval

Shared POST forms include **csrf_token**. CsrfViewMiddleware checks that token
on browser form actions.

approve_donor() also requires active staff status and users.change_user.
Within a transaction it locks an active donor account and changes only
support_approved when approval is needed. Repeated approval is idempotent:
an already approved account remains approved. Name, role, password and other
privileges are preserved, and the existing approval signal handles notification.

## 11. Notifications, maps and update polling

### 11.1 Notifications connect through signals

A Django **signal** lets a registered function react when another operation
occurs. This project uses model save signals for updates:

~~~text
DashboardConfig.ready()
    -> imports dashboard/signals.py
    -> connects model save handlers

Workflow/account code saves a relevant record
    -> signal handler selects recipients and message
    -> notify_after_commit() schedules a callback
    -> database transaction commits successfully
    -> callback creates recipient-owned Notification rows
    -> inbox and unread-count context processor display them
~~~

| Saved record/change | Handler in signals.py | Notification purpose |
| --- | --- | --- |
| New StatusEvent | lifecycle_update() | Request arrival and lifecycle changes |
| New non-verified Verification | review_update() | Review decision or requester response; verified changes use the lifecycle event |
| Offered/withdrawn Donation | pledge_update() | A support offer changed |
| Changed User.support_approved | remember_approval() and approval_update() | The donor's approval status changed |

**transaction.on_commit(deliver, robust=True)** runs the notification callback
after successful database commit. A rolled-back workflow does not create its
notification, and a callback failure does not undo the committed relief action.
This callback runs through Django's transaction handling in the application
process.

Notifications omit private notes/contact information, exclude the acting user
where an actor is supplied and target active recipients. The database's
recipient/event_key uniqueness constraint prevents duplicate messages for the
same event and recipient. Read actions update only the current user's inbox.

The implemented notification channel is the persistent in-app inbox. Email
backend settings exist in the environment configurations; email/SMS delivery
remains planned optional integration work.

### 11.2 The optional map

**maps.py** selects requests in Verified, Assigned, In progress or Delivered.
It applies category/urgency filters and prepares up to 250 prioritized rows.
The row dictionary explicitly contains public fields, public-area text and
rounded coordinates.

The template outputs a usable area list first. It places the selected map data
in a **json_script** block: JSON safely embedded for JavaScript to read.
When there is a configured browser key and located data, the user can load the
interactive map.

**map.js** reads that JSON and loads Google's Maps JavaScript API. It uses
markers, bounds and info windows with public descriptions/links. Loading,
authentication or runtime failure produces fallback feedback; a 12-second
timeout also returns the user to the area-list presentation.

Requests without coordinates still appear in the selected area-list results.
Core submissions/reviews/delivery do not call Google Maps.

### 11.3 Status updates and displayed relative times

Two kinds of time-related browser behavior have different jobs:

| Behavior | Files | Effect |
| --- | --- | --- |
| Relative timestamp display | motion.js and time[data-relative] | Appends labels such as “4 min ago” to an already rendered absolute timestamp |
| Fresh-data detection | updates.js and JSON snapshot views | Detects a changed server revision and offers a page refresh |

The public **board_updates()** snapshot returns a revision made from request
count and latest updated_at. The authorized **request_updates()** snapshot
returns the request's updated_at revision, current status and status label.
The snapshot routes are read-only and marked never_cache.

updates.js checks about every 30 seconds while the page is visible. It uses
same-origin fetch with no-store caching and an eight-second abort timeout.
When it detects a change it shows a notice and stops checking until the page
is refreshed. It does not replace the current form values; the user chooses
the Refresh button.

The model's updated_at is also touched by review responses and pledge changes,
so the snapshot can indicate new work even when the lifecycle status is the
same. This is polling-based visibility of server changes.

### 11.4 How the acknowledgement and receipt metrics are calculated

ReliefRequestQuerySet.acknowledgement_stats() gathers each acknowledged
request's elapsed minutes:

~~~text
acknowledgement minutes = (acknowledged_at - submitted_at) in minutes
~~~

It sorts the values and takes the middle value, or averages the two middle
values for an even-sized set. It also counts requests within the target and
unacknowledged requests waiting beyond the target.

The coordinator dashboard calculates confirmation coverage from Delivery
records with a delivered_at timestamp:

~~~text
confirmation coverage =
    delivered records with recipient_confirmed_at / all delivered records
~~~

The displayed seed-data metrics demonstrate the calculation. The
[controlled pilot](PILOT_PLAN.md) is where real acknowledgement performance and
usability measurements are to be collected.

## 12. Configuration, startup and migrations

### 12.1 Configuration values

base.py imports values from the process environment and local .env. The helper
functions env(), env_bool() and env_list() convert strings into the expected
setting types.

| Setting | Effect |
| --- | --- |
| DJANGO_SETTINGS_MODULE | Selects the settings module before Django startup; default entry points choose config.settings.dev |
| SECRET_KEY | Supports Django's signing/session/security machinery; production rejects the missing/development placeholder |
| DEBUG | Controls development behavior; production settings fix it to false |
| ALLOWED_HOSTS | Defines accepted hostnames |
| TIME_ZONE | Controls configured display timezone; defaults to Asia/Kolkata with timezone-aware datetimes enabled |
| ACKNOWLEDGEMENT_TARGET_HOURS | Target used by model queries, metrics and labels; default 2 |
| ENABLE_IN_APP_NOTIFICATIONS | Enables creation of new in-app updates; default true |
| GOOGLE_MAPS_API_KEY | Browser Maps JavaScript API key for the optional map |
| POSTGRES_DB / USER / PASSWORD / HOST / PORT | Production database connection settings |
| SECURE_SSL_REDIRECT | Turns on HTTPS redirect and related secure-cookie/HSTS settings when the HTTPS environment is configured |
| CSRF_TRUSTED_ORIGINS | Production setting for trusted cross-origin browser form origins when needed |

Select production in the **process environment** before launching an entry
point. The local .env is loaded by the already selected base settings module.
See [README.md](../README.md) for the complete existing setup instructions.

### 12.2 What happens when you start the app

~~~text
.venv Python runs manage.py runserver
    -> choose settings module
    -> load base/environment-specific settings and .env
    -> register installed Django/project apps
    -> initialize model registry and admin registrations
    -> DashboardConfig.ready() connects notification signals
    -> load root/app routes
    -> listen for browser requests
~~~

For an already prepared local environment:

~~~powershell
.\.venv\Scripts\python.exe manage.py runserver
~~~

For a new environment, follow the README's virtual-environment, dependency,
configuration, migrate and seed steps first. Local browser access is normally
at http://127.0.0.1:8000/.

The development server serves authored files from static/. Production storage
uses **collectstatic**, which gathers project assets and Django admin assets
into STATIC_ROOT. WhiteNoise's manifest storage creates hashed asset filenames;
the template's static tag resolves the correct URL.

### 12.3 Migration files: the database's structural history

Models describe the intended current schema. A **migration** describes a
change to that schema. makemigrations generates migration code; migrate applies
unapplied migration operations to the selected database. Django records applied
versions in django_migrations.

| Migration file | Schema work |
| --- | --- |
| [users/0001_initial.py](../apps/users/migrations/0001_initial.py) | Creates Role and custom User, including Django auth relationships |
| [users/0002_user_support_approved.py](../apps/users/migrations/0002_user_support_approved.py) | Adds donor support approval |
| [requests/0001_initial.py](../apps/requests/migrations/0001_initial.py) | Creates core ReliefRequest and StatusEvent structures |
| [requests/0002_initial.py](../apps/requests/migrations/0002_initial.py) | Adds user/request relationships and request indexes |
| [requests/0003_reliefrequest_evidence_name_reliefrequest_latitude_and_more.py](../apps/requests/migrations/0003_reliefrequest_evidence_name_reliefrequest_latitude_and_more.py) | Adds public area, optional coordinates and request evidence/name fields |
| [verification/0001_initial.py](../apps/verification/migrations/0001_initial.py) | Creates retained review/response records and evidence fields |
| [donations/0001_initial.py](../apps/donations/migrations/0001_initial.py) | Creates support pledges |
| [delivery/0001_initial.py](../apps/delivery/migrations/0001_initial.py) | Creates delivery fields and initial user links |
| [delivery/0002_initial.py](../apps/delivery/migrations/0002_initial.py) | Adds request, donation and responder links |
| [dashboard/0001_initial.py](../apps/dashboard/migrations/0001_initial.py) | Creates Notification with recipient/event uniqueness and inbox index |

Migration dependencies arrange operations across apps, including links to the
custom User model. The two initial files in requests/delivery split creation
and relationship operations to satisfy those dependencies.

These commands inspect configuration/schema alignment:

~~~powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py showmigrations
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
~~~

For an intentional new model-field change, the development sequence is to
update the model and affected forms/pages, generate its migration and apply it.
Existing applied migration files are the recorded schema history.

## 13. Tests, demo data and project documents

### 13.1 Automated test files

| File | What it verifies |
| --- | --- |
| [users/tests.py](../apps/users/tests.py) | Password hashing, permitted registration, login behavior, approval state and logout |
| [users/test_account_management.py](../apps/users/test_account_management.py) | Account-management permissions, read-only access, CSRF, POST-only/idempotent approval, retained privileges, filters and pagination |
| [requests/tests/helpers.py](../apps/requests/tests/helpers.py) | WorkflowTestCase fixtures and helpers for requests, reviews, assignment and delivery |
| [requests/tests/test_workflow.py](../apps/requests/tests/test_workflow.py) | Lifecycle ordering, actor permissions, review/support/delivery rules, transactional behavior and metrics |
| [requests/tests/test_views.py](../apps/requests/tests/test_views.py) | Submission/actions, forms, private/public data boundaries and upload/download behavior |
| [requests/tests/test_demo.py](../apps/requests/tests/test_demo.py) | Demonstration seeding, idempotence and preservation of non-demo records |
| [dashboard/tests.py](../apps/dashboard/tests.py) | Notifications/commit behavior, owner-scoped visibility, role workspaces, map privacy/fallback and update snapshots |

The latest recorded regression result is **82 passing tests**, documented in
work-log entry 007 and TEST_REPORT.md. These are Django tests using an isolated
test database. Workflow tests make calls to the same services used by pages.

The suite is run with:

~~~powershell
.\.venv\Scripts\python.exe manage.py test --noinput
~~~

Automated tests verify backend behavior; browser checks additionally exercise
rendered pages, form interactions, role menus and responsive layout.
The local browser scripts under .local use Node.js to control Edge and separate
verification databases/media, preserving the working project's records.
Their reports/screenshots are referenced in the test report.

### 13.2 Demonstration data

seed_demo.py is a Django **management command** discovered through the
management/commands package. Running `manage.py seed_demo` creates the four
fictional role accounts and nine sample requests when they do not already
exist.

It uses actual review, pledge and delivery services for new sample workflows.
Backdated timestamps give the dashboard meaningful demonstration metrics.
Matching older fictional rows can be enriched with supporting records while
their existing lifecycle history is retained.

Existing account passwords are preserved. The optional **--fresh** mode
rebuilds matching sample requests while keeping other requests and accounts.
The command requires DEBUG true. The current working database can contain
additional requests from later application use, so its total need not be nine.

The [README's demonstration accounts](../README.md#demonstration-accounts)
contain the emails and common demo password.

### 13.3 Documentation files

| File | What to use it for |
| --- | --- |
| [README.md](../README.md) | Installation, demo credentials, feature overview, demonstration flow and production setup |
| [docs/floodrelief-proposal.pdf](floodrelief-proposal.pdf) | Canonical proposal: requirements, workflow, privacy, evaluation and milestones |
| [root floodrelief_proposal.pdf](../floodrelief_proposal.pdf) | Separate existing proposal file retained in the workspace; the docs PDF is the designated reference |
| [PROJECT_PROGRESS.md](PROJECT_PROGRESS.md) | Current checkpoint, project plan and consecutive numbered work log |
| [TEST_REPORT.md](TEST_REPORT.md) | Automated/browser results, local evidence and remaining validation |
| [PILOT_PLAN.md](PILOT_PLAN.md) | Representative-role tasks and measurement plan for a real pilot |
| [diagrams/README.md](diagrams/README.md) | Maps proposal use cases to implemented routes |
| [diagrams/architecture.md](diagrams/architecture.md) | Existing architecture, entity and workflow diagrams |
| [diagrams/proposal-usecase-p6.png](diagrams/proposal-usecase-p6.png) | Original use-case diagram extracted from proposal page 6 |
| This PROJECT_GUIDE.md | Detailed file responsibilities, technology explanations and code-reading route |

Mermaid diagrams render in compatible Markdown viewers. The surrounding
tables and explanations describe the same relationships when a viewer
displays the diagram source.

Live Google Maps configuration, physical-device/connection checks, PostgreSQL
staging and the controlled pilot remain planned validation. Production settings
and static collection have been checked locally; that is separate from a live
deployment.

## 14. Where to change what

Use this table when you have a concrete feature or interface change in mind.
Follow the existing service path for changes to workflow behavior.

| Intended change | Files to start with | Related parts to inspect |
| --- | --- | --- |
| Shared colors/fonts/design values | static/css/base.css; templates/base.html | Other CSS uses the shared tokens; base.html loads font families |
| Public board card spacing | static/css/board.css; partials/request_card.html | Shared badges/tracker in components.css |
| Workspace card/filter/table alignment | static/css/workspace.css; relevant workspace partial/page | Shared input rules in form.css and role data from dashboard/views.py |
| Shared form field appearance | templates/partials/field.html; static/css/form.css | Form widgets/labels in the relevant forms.py; ui.js for error/password interaction |
| Add a submission field | requests/models.py and forms.py; requests/request_form.html | Migration, privacy presentation, upload rules if applicable and affected tests |
| Beneficiary/donor/NGO/admin dashboard content | dashboard/views.py; templates/dashboard/roles/ | home.html, dashboard_metrics.html and workspace_nav.html |
| Role menu or primary action | workspace_nav.html and header_action.html | User.workspace_role / permission properties and dashboard action context |
| Review decisions or response rules | verification/forms.py and services.py | Request transition validation, request_detail(), review history and notification handlers |
| Support-offer requirements | donations/forms.py and services.py | Donor approval, request stage, pledge ownership and workflow tests |
| Assignment or receipt requirements | delivery/forms.py and services.py | Delivery model, request transition validation, action panels and workflow tests |
| Who can open private records | requests/permissions.py and evidence/proof views | Workbench private_details context and public-safe templates |
| Donor approval/account oversight | users/account_views.py and models.py | User admin, manage_accounts.html, approval signal and account-management tests |
| Notification recipients/content | dashboard/signals.py and notifications.py | After-commit handling, Notification uniqueness and recipient ownership tests |
| Map fields/filtering | dashboard/maps.py and dashboard/map.html | Safe serialization, coordinate rounding and map.js |
| Polling behavior or update notice | static/js/updates.js and update_notice.html | Snapshot views and the request updated_at changes |
| Acknowledgement metric | requests/models.py | First-review acknowledge() calls, dashboard/board queries, presentation and metric tests |
| Add a page | Relevant app urls.py and views.py; new template | Root prefix, role access, navigation and required static assets |
| Deployment/database settings | config/settings/production.py and .env.example | Process environment, WSGI/ASGI entry point, collectstatic and hosting setup |

A visible behavior can span several files. For example, changing a receipt
requirement involves the form, service, model transition rule and displayed
helper text; changing only a label changes presentation.

## 15. A practical reading and debugging path

### 15.1 Recommended reading order

1. Read the README's demonstration flow and open the four role workspaces.
2. Open config/urls.py and requests/urls.py to find /requests/new/ and the
   private workbench route.
3. Read RequestCreateView beside ReliefRequestForm and request_form.html.
   Identify where input becomes validated data and where the HTML is generated.
4. Read ReliefRequest.save(), StatusEvent and transition_to() in models.py.
   Follow creation of the reference and initial event.
5. Read request_detail() beside request_detail.html and action_form.html.
   Follow one hidden action value to its permission check, form and service.
6. Follow review_request(), pledge_support() and the four delivery service
   functions in workflow order.
7. Read User permission properties and can_view_request() to understand why
   the same request page can expose different actions/information.
8. Read dashboard.home() beside home.html and the four role templates.
9. Read DashboardConfig.ready(), signals.py and notify_after_commit() to see
   the secondary notification path.
10. Read one matching test, such as a lifecycle or account-approval test, to
    see a concrete verified scenario.
11. Follow HTML classes/data attributes into the relevant CSS/JavaScript file.
12. Use the project progress and pilot/test documents to see the next planned work.

In an editor, searching for a **URL name**, **action value**, **context key**,
**CSS class** or **data attribute** is often the quickest way to follow a
connection. For example, search for transition_to, can_confirm,
data-status-watch or workspace-grid.

### 15.2 Following a problem to the right layer

| Symptom/question | What to inspect |
| --- | --- |
| “Which code serves this URL?” | config/urls.py, then the selected app urls.py and view |
| “Where does this displayed value come from?” | Template variable, view context, then its query/model property |
| “Why is a button missing?” | Template condition and the corresponding role/stage flag in request_detail() or home() |
| “Why did my form fail?” | Field/form errors, forms.py clean methods and service ValidationError checks |
| “Why is a donor awaiting approval?” | User.support_approved, can_support and the authorized account approval page |
| “Why can NGO staff not manage accounts?” | is_staff plus users.view_user/change_user checks; the NGO coordination role is a different permission |
| “Why did a rejection stay at Received?” | Verification decision history and review_request(); acknowledgement and lifecycle are separate |
| “Why is an older request absent from the dashboard?” | Six-request preview; use filtered /dashboard/activity/ |
| “Why is a file unavailable?” | Correct record UUID, owner/coordinator/responder check, model FileField and stored file existence |
| “Why does Maps not load?” | Configured browser key/located rows, map.js feedback and the server-rendered area list |
| “Why is a new change not visible?” | A full refresh or update notice, server autoreloading and collected static assets in production |
| “Why does startup mention missing tables?” | Applied migrations in the selected database |
| “Why cannot Python import Django?” | Selected .venv interpreter and installed requirements |

The normal development server autoreloads. A server started with --noreload
needs a restart after Python/template changes so it uses refreshed code/templates.
Development CSS comes from static/; a production static change requires updated
collectstatic output.

## 16. Glossary

| Term | Meaning in this project |
| --- | --- |
| Backend | Python/Django code that handles requests, business rules and storage |
| Frontend | HTML, CSS and JavaScript that the browser presents/interacts with |
| Route / URL pattern | A mapping from a browser path to a Django view |
| Middleware | Shared request/response handling around views, such as sessions and CSRF |
| View | A Python handler that reads input, checks access and returns a response |
| Context | Named values a view supplies when rendering a template |
| Template / partial | HTML with Django expressions; a partial is a reusable fragment |
| Model | A Python definition of stored data and associated behavior |
| ORM / QuerySet | Django's database-query layer and a composable selection of records |
| Form / ModelForm | Input validation and field rendering; ModelForm is connected to a model |
| Service | A reusable function that carries out a complete workflow operation |
| Migration | Versioned code that changes the database structure |
| Foreign key | A database relationship to another model's record |
| One-to-one | A unique relationship, such as a request's lead Delivery |
| UUID / reference | Internal record identity / short human-readable tracking code |
| Transaction / commit | A grouped database operation / its successful finalization |
| Signal | A registered callback reacting to an event such as model save |
| Session | Server-side state used to remember an authenticated browser |
| CSRF token | A form token checked to protect authenticated browser actions |
| Static / media | Authored interface assets / uploaded file bytes |
| JSON | A structured data format used by update snapshots and map data |
| Polling | Periodically asking the server whether information changed |
| WSGI / ASGI | Interfaces connecting Django to a web application server |
| Progressive enhancement | Adding browser conveniences while keeping basic HTML/form tasks usable |
| ARIA | Accessible labels/states that help assistive technologies describe controls and feedback |
