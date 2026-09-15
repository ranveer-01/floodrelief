# Diagrams

## In this folder

- **`proposal-usecase-p6.png`** — the use-case diagram from page 6 of the
  proposal, extracted from the PDF so it can be referenced without opening it.
  Four actors: *victim*, *official authorities*, *Donors/NGO*, *administrators*.

The proposal itself is one level up at `docs/floodrelief-proposal.pdf`.

## Still to add

Drop the remaining UML diagrams here as you finish them — class diagram,
sequence diagram for the status workflow, ER diagram. Export as PNG or SVG and
name them `class-diagram.png`, `sequence-status-flow.png`, and so on.

## How the use-case diagram maps to the code

| Use case | Actor | Where it lives |
| --- | --- | --- |
| sends request | victim | `/requests/new/` — `apps/requests/views.py:RequestCreateView` |
| Track request status | victim | `/requests/` — `RequestListView`, plus the per-card audit trail |
| Authenticate user | all | `apps.users.User` (email login), Django admin session auth |
| verify and browse requests | official authorities | admin list + the *Mark verified* bulk action |
| Update the status | official authorities | `ReliefRequest.transition_to()` — the only write path |
| authorise and confirm request delivery | official authorities | *Mark delivered* / *Close* bulk actions |
| browse throw the verified request | Donors/NGO | `/requests/?status=verified` |
| manage users | administrators | `apps/users/admin.py` |
| manage dashboard and website workflow | administrators | `/admin/`, landing metrics from `acknowledgement_stats()` |

Not built yet — these are the milestone-2 apps that currently hold only a
docstring: **contribute and offer supports** (`apps/donations/`), **Upload
delivery proof** (`apps/delivery/`), and the reviewer queue behind **verify and
browse requests** (`apps/verification/`). Verification and delivery are
reachable through the admin today; the dedicated staff-facing screens are what
those apps will add.
