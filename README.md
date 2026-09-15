# FloodRelief Connect

A web platform that gives flood relief requests **one traceable record** instead
of scattering them across phone calls, WhatsApp groups, and paper forms.

Every request gets a reference code the moment it arrives, then moves through a
six-stage lifecycle where **each transition is timestamped and kept**:

```
Received → Verified → Assigned → In Progress → Delivered → Closed
```

Semester software project by **Ranveer Singh** (1024170100) and **Manshaan
Singh** (1024170110), submitted to Sandeep Kaur. Built against
`docs/floodrelief-proposal.pdf`.

---

## The primary metric

The proposal names one headline measure:

> The primary evaluation measure will be **time to acknowledgement /
> verification**, calculated from the request-submission timestamp to the first
> meaningful staff action. A pilot target will be a **median acknowledgement
> time of less than two hours**.

That is implemented literally, not decoratively:

- `submitted_at` is stamped on creation; `acknowledged_at` is stamped on the
  first transition *away from* `received` — i.e. the first meaningful staff
  action, exactly as defined above.
- `ReliefRequestQuerySet.acknowledgement_stats()` reports the **median** (not
  the mean — one stale request shouldn't be hidden by averaging), the
  within-target percentage, and how many are currently breaching.
- The target is configurable: `ACKNOWLEDGEMENT_TARGET_HOURS`, default `2`.
- Those numbers are on the landing page and the board, and every card shows its
  own acknowledgement delta colour-coded good / late / overdue / waiting.

---

## Quick start

Requires Python 3.13 (developed on 3.13.2 with Django 5.2.17).

```bash
python -m venv .venv
source .venv/Scripts/activate     # Windows bash; use .venv\Scripts\activate on cmd
                                  # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env              # dev defaults work as-is

python manage.py migrate
python manage.py seed_demo        # 4 roles, a demo NGO user, 9 realistic requests
python manage.py createsuperuser  # prompts for email + name (there is no username)
python manage.py runserver
```

Then open <http://127.0.0.1:8000/>.

`seed_demo` backdates its timestamps, so the median-acknowledgement figure is a
real calculation over spread-out data rather than a hardcoded number. Re-run
with `--fresh` to wipe and rebuild the demo rows.

It also creates a demo NGO staff login: **`staff@floodrelief.test`** /
**`floodrelief`** (dev only — the account is pointless in production).

### Pages

| URL | What it is |
| --- | --- |
| `/` | Landing — the problem, the lifecycle, live metrics |
| `/requests/new/` | Submit a relief request |
| `/requests/` | The board: every request, filterable, with live timestamps |
| `/admin/` | Coordination desk — verify, assign, deliver, close |

---

## The demo flow

1. Start at `/` — the metric strip is reading the real database.
2. **Submit a request** → fill the form → submit. The button locks and stamps
   the send time.
3. You land on `/requests/`, scrolled to your new request, which arrives with a
   *Just submitted* flag and an animated status tracker at **Received**.
4. Open **Audit trail** on the card — one event, timestamped, `→ Received`.
5. Go to `/admin/requests/reliefrequest/`, open that same row (same reference
   code), change status to **Verified**, save.
6. Back on `/requests/`: the tracker has advanced, and *Time to
   acknowledgement* has switched from waiting to a real duration. The audit
   trail now has two events, the second attributed to your admin user.

Step 6 is the point of the project: the status did not just change, the
**change itself was recorded**.

---

## Data model

`apps/users/`

- **`Role`** — uuid pk, name (`victim` / `donor` / `ngo_staff` / `admin`),
  description. The four actors from the use-case diagram.
- **`User`** — uuid pk, name, email (the login field — no username), phone,
  role FK, `created_at`, plus the standard active/staff flags. Custom
  `AbstractBaseUser` with `UserManager`, wired up as `AUTH_USER_MODEL`.

`apps/requests/`

- **`ReliefRequest`** — uuid pk, `reference`, `submitted_by` FK, category,
  description, location, urgency, status, `contact_name`, `contact_phone`,
  `people_affected`, `submitted_at`, `updated_at`, `acknowledged_at`,
  `closed_at`.
- **`StatusEvent`** — one row per lifecycle transition: `from_status`,
  `to_status`, `changed_by`, `note`, `changed_at`. Append-only in practice;
  read-only in the admin.

### Fields beyond the class diagram

The class diagram lists `ReliefRequest` as id / submittedBy / category /
description / location / urgency / status / submittedAt. The additions all come
from the proposal body rather than from invention:

| Added | Why |
| --- | --- |
| `reference` | The proposal's week 3–4 deliverable is "request ID generation", and §3.3 says a victim "receives a unique request ID". Format `FRC-XXX-XXX`, generated from an unambiguous alphabet (no `O`/`0`/`I`/`1`) so it survives being read aloud over a phone. |
| `StatusEvent` model | §3.3: "Each transition will be recorded in the status history so that the system can reconstruct what happened and when." Week 5–6 deliverable is literally "status history". |
| `contact_name`, `contact_phone` | §3.2 lists "contact information" in the relief-request module. Required, so a request submitted by an unauthenticated victim is still reachable. |
| `acknowledged_at` | Needed to compute the proposal's own primary metric. |
| `closed_at`, `updated_at` | Closure timestamp for lifecycle reporting; `updated_at` for ordinary change tracking. |
| `people_affected` | Our own addition — triage needs scale, not just urgency. The one field here with no line in the proposal behind it. |

### One write path

Status is only ever changed through `ReliefRequest.transition_to(new_status,
by=..., note=...)`, which stamps the clock, sets `acknowledged_at` on first
action, and appends the `StatusEvent`. The admin's `save_model` and all five
bulk actions route through it, so **the audit trail cannot be bypassed by
editing through the admin** — verified by test.

---

## Project layout

```
config/settings/     base.py, dev.py, production.py
apps/users/          custom user + roles                     [built]
apps/requests/       lifecycle, board, submission form        [built]
apps/dashboard/      landing page + live metrics              [built]
apps/verification/   reviewer queue                           [milestone 2]
apps/donations/      donor pledges against verified requests  [milestone 2]
apps/delivery/       assignment + proof of delivery           [milestone 2]
templates/           base.html, partials/, per-app templates
static/css/          base, components, landing, form, board
static/js/           motion.js, form.js, board.js
docs/                proposal PDF + diagrams/
```

The three milestone-2 apps are registered and migration-ready but hold only a
docstring describing their scope. Verification and delivery are both *usable*
today through the admin — those apps add the dedicated staff screens. This
mirrors the proposal's own instruction to get the minimum end-to-end workflow
stable before adding modules.

---

## Frontend

Plain HTML, CSS, and JavaScript. No React, no Bootstrap, no CSS framework, no
build step — what's in `static/` is what the browser gets.

- Custom design tokens in `static/css/base.css`; layouts are 12-column CSS Grid,
  deliberately asymmetric rather than centred cards.
- Type: Fraunces (display) / Archivo (body) / JetBrains Mono — every timestamp
  and reference code is monospaced, because they're data.
- Motion is 150–400 ms and cheap: `IntersectionObserver` reveals,
  `requestAnimationFrame`-throttled scroll, CSS transforms only. Everything is
  wrapped in `prefers-reduced-motion` guards, and the pages work fully with
  JavaScript disabled (`.no-js` draws the trackers in place).
- Timestamps show the absolute stamp *and* a live relative suffix, refreshed
  every 30 s. The absolute value is never replaced.
- Photography is real disaster-response work, credited with licences in
  **`static/images/CREDITS.md`**. Each photo sits under a duotone scrim with a
  gradient fallback, so a missing image degrades to a deliberate colour field.

---

## Production

`config/settings/production.py` refuses to start on a missing, empty, or
dev-placeholder `SECRET_KEY`, or with an empty `ALLOWED_HOSTS` — a loud failure
beats silently serving with a known key. It switches to PostgreSQL, inserts
WhiteNoise, turns on HSTS / secure cookies / referrer policy, and uses
`CompressedManifestStaticFilesStorage`.

```bash
export DJANGO_SETTINGS_MODULE=config.settings.production
# set SECRET_KEY, ALLOWED_HOSTS, POSTGRES_* — see .env.example
python manage.py migrate
python manage.py collectstatic --noinput
gunicorn config.wsgi:application
```

## Status

Working end to end and verified: the three pages, the submission round trip, the
filters, the admin, `transition_to`, the audit trail surviving an admin edit, and
`collectstatic` under production settings.

Not built yet: donor pledges, delivery proof upload, the dedicated verification
queue, the Google Maps view, and notifications — all scheduled after the core
workflow, per the proposal's phase plan. There is no automated test suite yet
either; verification so far has been a scripted end-to-end pass, and §3.4's
unit/integration tests are still to write.
