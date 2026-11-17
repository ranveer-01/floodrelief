# Proposal use cases and implementation

The canonical reference is [floodrelief-proposal.pdf](../floodrelief-proposal.pdf).
[proposal-usecase-p6.png](proposal-usecase-p6.png) contains the original use-case
diagram from page 6.

The proposal describes victims, official authorities, donors/NGOs, and
administrators. In the application, authorized officials use the NGO staff role;
approved donors and NGO staff can offer support.

| Use case | Actor | Implemented route or component |
| --- | --- | --- |
| Send a request | Beneficiary, including anonymous phone/walk-in entries | `/requests/new/` |
| Track request status | Beneficiary and public viewers | `/requests/`; private `/requests/<uuid>/` |
| Authenticate user | Registered roles | `/accounts/register/`, `/accounts/login/`; email-based custom user |
| Verify and browse requests | Authorized staff | `/verification/` and request review forms |
| Request additional information | Staff and beneficiary | Retained review history and requester response form |
| Update status | Authorized coordinator/assigned responder | Lifecycle services and retained `StatusEvent` records |
| Browse verified requests | Approved donors/NGO staff | `/support/` |
| Contribute or offer support | Approved donors/NGO staff | Goods, transport, and INR pledge form; own pledge history |
| Assign a responder | Authorized staff | Assignment form linked to an approved available pledge |
| Upload delivery proof | Assigned responder/staff | Private optional JPEG, PNG, or PDF upload |
| Authorize and confirm delivery | Responder, beneficiary, authorized staff | Hand-over record followed by recipient confirmation before closure |
| Manage users | Administrator with Django user-management permissions | `/accounts/manage/` for account oversight/donor approval; `/admin/users/user/` for full account administration |
| Manage dashboard/workflow | Staff/administrator | Distinct role dashboards, all-operations activity, read-only record admin |
| View affected areas | Public users and responders | `/map/`, coarsened locations, and a working area-list fallback |
| Receive updates | Signed-in account owner | Private `/dashboard/notifications/` inbox and update polling |

[architecture.md](architecture.md) adds an architecture diagram, entity
relationships, and the full status workflow sequence for the implemented
prototype.

The software flow is implemented and verified locally. Live Maps configuration,
physical-device checks, PostgreSQL staging, and the controlled pilot are
tracked in [the project plan](../PROJECT_PROGRESS.md).
