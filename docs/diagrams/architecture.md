# Architecture and lifecycle diagrams

These diagrams describe the implemented prototype and supplement the proposal's
use-case diagram.

## Architecture

~~~mermaid
flowchart LR
    Browser["Browser: HTML, CSS, JavaScript"] --> Views["Django views and role checks"]
    Views --> Forms["Validated forms"]
    Forms --> Services["Review, support and delivery services"]
    Services --> Lifecycle["Ordered request transitions"]
    Lifecycle --> DB[("SQLite development / PostgreSQL production")]
    Lifecycle --> Events["Retained status events"]
    Events --> DB
    Services --> Records["Review, pledge and delivery records"]
    Records --> DB
    DB --> Dashboard["Dashboards and acknowledgement metrics"]
    Dashboard --> Views
    Services -. after commit .-> Inbox["Recipient-owned in-app notifications"]
    Inbox --> DB
    Views --> Evidence["Authorized attachment downloads"]
    Views --> Public["Public status and approximate area data"]
    Public --> Browser
    Browser -. optional load .-> Maps["Google Maps"]
~~~

The public area list and all relief actions remain available without Google
Maps. Notification callbacks run after the relief transaction commits.

## Entity relationships

~~~mermaid
erDiagram
    ROLE o|--o{ USER : grants_role
    USER o|--o{ RELIEF_REQUEST : submits
    RELIEF_REQUEST ||--|{ STATUS_EVENT : retains
    USER o|--o{ STATUS_EVENT : changes
    RELIEF_REQUEST ||--o{ VERIFICATION : has_reviews
    USER ||--o{ VERIFICATION : records
    RELIEF_REQUEST ||--o{ DONATION : receives_offers
    USER ||--o{ DONATION : offers
    RELIEF_REQUEST ||--o| DELIVERY : has_lead_delivery
    DONATION ||--o| DELIVERY : assigned_offer
    USER ||--o{ DELIVERY : responds
    USER ||--o{ NOTIFICATION : receives
    RELIEF_REQUEST o|--o{ NOTIFICATION : concerns
~~~

`Delivery` additionally retains the assigning user and the confirming user.
Request/review evidence and delivery proof include private file metadata.
Account approval notifications can have no associated request.

## Full workflow sequence

~~~mermaid
sequenceDiagram
    actor Beneficiary
    actor Staff
    actor Donor
    participant App as Django services
    participant DB as Request and audit records
    participant Inbox as In-app inbox
    Beneficiary->>App: Submit valid request
    App->>DB: Received + reference + initial event
    Staff->>App: Verify with method and notes
    App->>DB: Retain review + first acknowledgement + Verified event
    App-->>Inbox: Notify beneficiary after commit
    Donor->>App: Offer goods, transport or funds
    App->>DB: Retain timestamped pledge
    Staff->>App: Assign available approved pledge
    App->>DB: Link lead responder + Assigned event
    App-->>Inbox: Notify responder and beneficiary after commit
    Donor->>App: Start assigned delivery
    App->>DB: Start timestamp + In progress event
    Donor->>App: Record recipient, hand-over notes and optional proof
    App->>DB: Delivery record + delivered pledge + Delivered event
    Beneficiary->>App: Confirm receipt with checkbox and notes
    App->>DB: Recipient confirmation + Closed event
    App-->>Inbox: Notify relevant accounts after commit
~~~

Staff can record recipient confirmation for a phone/anonymous entry. Rejection
and more-information decisions retain review history and acknowledge first staff
action while the lifecycle stays at Received. A beneficiary response returns the
review decision to pending; a fresh staff decision is required to verify.
