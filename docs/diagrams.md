# Delivery prototype diagrams

These diagrams cover the proposed P0–P2 architecture, from the first catalog page through manual delivery. [Implementation plan](plan.md) · [Specification](specs.md)

## System architecture

Customers browse and place orders, merchants prepare them, dispatch staff assign drivers, and drivers confirm pickup and delivery. Each role uses the same Django application with its own permissions.

```mermaid
flowchart TB
    Customer[Customer browser] --> Web
    Merchant[Merchant browser] --> Web
    Staff[Staff browser] --> Web
    Driver[Driver browser] --> Web

    subgraph Compose["Docker Compose"]
        subgraph Django["Django application"]
            Web["Views, templates, and forms"]
            Accounts["accounts · sessions and roles"]
            Catalog["catalog · merchants and products"]
            Orders["orders · checkout, transitions, and events"]
            Deliveries["deliveries · driver assignments"]

            Web --> Accounts
            Web --> Catalog
            Web --> Orders
            Web -->|Read assigned deliveries| Deliveries
            Orders -->|Read prices and availability| Catalog
            Orders -->|Create assignment| Deliveries
        end
        DB[("PostgreSQL")]
        Accounts --> DB
        Catalog --> DB
        Orders --> DB
        Deliveries --> DB
    end
```

`orders` owns all lifecycle transitions, including staff assignment and driver confirmations. Django Admin manages demo accounts and catalog records and provides read-only access to order, delivery, and event records.

## Order lifecycle

Each arrow identifies the actor and action. P1 ends at **Ready**. P2 takes the order through **Delivered**. Each successful action records one status event.

```mermaid
stateDiagram-v2
    state "Picked up" as PickedUp
    [*] --> Placed: Customer places order
    Placed --> Accepted: Merchant accepts order
    Accepted --> Ready: Merchant marks order ready
    Ready --> Assigned: Staff assigns an active driver
    Assigned --> PickedUp: Assigned driver confirms pickup
    PickedUp --> Delivered: Assigned driver confirms delivery
    Delivered --> [*]
```

The customer sees the current state and ordered event history when they refresh the order page. **Delivered** is terminal.

## Core data relationships

```mermaid
erDiagram
    MERCHANT ||--o{ PRODUCT : offers
    MERCHANT ||--o{ CUSTOMER_ORDER : receives
    ACCOUNT ||--o{ CUSTOMER_ORDER : places
    CUSTOMER_ORDER ||--|{ ORDER_ITEM : contains
    PRODUCT ||--o{ ORDER_ITEM : referenced_by
    CUSTOMER_ORDER ||--o| DELIVERY : has
    ACCOUNT ||--o{ DELIVERY : drives
    CUSTOMER_ORDER ||--|{ ORDER_STATUS_EVENT : records
    ACCOUNT ||--o{ ORDER_STATUS_EVENT : acts
```

Each order belongs to one merchant. The order keeps the delivery address and total at checkout, and its items keep the product names and unit prices at checkout. The order has a unique customer and submission key pair for safe checkout retries. A delivery record is created on assignment, and status events store the actor, the state change, and the time.

## Driver assignment transaction

Assignment shows how the workflow keeps the order state, delivery, and event consistent. If staff submit competing assignments, the second request to acquire the order lock sees the committed **Assigned** state and is rejected.

```mermaid
sequenceDiagram
    actor Staff as Dispatch staff
    participant View as Django view
    participant Orders as Order workflow
    participant DB as PostgreSQL

    Staff->>View: Submit driver assignment
    View->>View: Validate session and CSRF token
    View->>Orders: Assign driver to order
    Orders->>DB: Begin transaction and lock order row
    DB-->>Orders: Return current state
    Orders->>Orders: Check staff permission, Ready state, and active driver
    alt Assignment is valid
        Orders->>DB: Create delivery, set Assigned, and append event
        Orders->>DB: Commit
        Orders-->>View: Assignment recorded
        View-->>Staff: Show updated order
    else Assignment is rejected
        Orders->>DB: End transaction without changes
        Orders-->>View: Rejection result
        View-->>Staff: Show rejection and order state if authorized
    end
```
