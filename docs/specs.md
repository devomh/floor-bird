# Delivery prototype specification

This specification covers P0–P2 of the [implementation plan](plan.md). The demonstration uses synthetic data, one merchant per order, simulated payment, web interfaces for all roles, and manual driver assignment. Each stage builds on the previous one.

## Architecture

One Django project serves web pages and form submissions. PostgreSQL stores the catalog, orders, deliveries, and event history. Run both with Docker Compose and use Django migrations and a repeatable demo seed command. Start with Django templates and forms.

| Module | Owns |
| --- | --- |
| `catalog` | Merchants, products, prices, and availability |
| `accounts` | Session authentication, role membership, and merchant and driver associations |
| `orders` | Checkout, order snapshots, lifecycle rules, and status events |
| `deliveries` | Driver assignments and delivery records |

Views that mutate order state call the same order workflow. Order, delivery, and event records are read-only in Django Admin. The workflow checks the actor, the current state, and any associated delivery. It locks the order row in a PostgreSQL transaction for existing-order transitions and commits related writes and the event together. Database constraints enforce one delivery per order and a unique customer and submission key pair on each order.

## Data and behavior

| Record | Required data or rule |
| --- | --- |
| Merchant and product | Each product belongs to a merchant and has a name, unit price in USD cents, and availability flag |
| Order | Customer, merchant, delivery address snapshot, total in USD cents, simulated payment marker, current state, and checkout submission key |
| Order item | Product reference, product name and unit price at checkout, and a positive integer quantity |
| Delivery | One per assigned order, with the assigned driver |
| Order status event | Order, previous and resulting states, acting user, and a server-generated timestamp |

- The catalog displays available products. Checkout requires a signed-in customer, a delivery address, and at least one available product from a single merchant. The server validates the selection and quantities, prices the order from the catalog, and rejects invalid input without creating an order. The total equals the sum of quantity times unit price. Fees, taxes, and tips are outside the prototype.
- An identical retry with the same customer and submission key returns the original order, including when the initial requests overlap. Reuse of that key with a different order payload is rejected. Store enough information to compare the requested products, quantities, and address without repricing a retry.
- Record the first event at checkout and one event for each successful transition. Display the current state and event history in transition order on the customer order page. Store timestamps in UTC.
- A rejected or stale transition leaves the order, delivery, and event history unchanged. Show a message with the current state when it is available to the signed-in actor. Once delivered, the order is terminal. Cancellation and reassignment are deferred.

## Lifecycle and access

| Action | State change | Authorized actor |
| --- | --- | --- |
| Place order | New → Placed | Signed-in customer |
| Accept order | Placed → Accepted | Merchant user for the order's merchant |
| Mark ready | Accepted → Ready | Merchant user for the order's merchant |
| Assign driver | Ready → Assigned | Authorized staff, selecting an active driver |
| Confirm pickup | Assigned → Picked up | Assigned driver |
| Confirm delivery | Picked up → Delivered | Assigned driver |

Customers can view their own orders, merchants can view orders for their own merchant, and drivers can view their own assigned deliveries. Staff with dispatch permission can view eligible orders and assign drivers. Enforce these rules on the server for reads and writes, including requests made directly to a URL. Show address details only where needed by the customer, assigned driver, and authorized staff. Keep addresses out of routine logs and the status event history. Use Django's session and CSRF protection for state-changing forms.

## Verification

| Prototype | Acceptance cases |
| --- | --- |
| P0 | A fresh Compose environment starts, migrations apply cleanly, the demo seed runs twice without duplicates, and the browser shows the persisted catalog. The PostgreSQL-backed CI job passes. |
| P1 | A customer creates one order and its initial event. A merchant accepts it and marks it ready. Later catalog price changes leave the order total intact. Invalid quantities, missing addresses, unavailable products, and mixed-merchant submissions create no orders. A retry with the same payload returns the original order, concurrent retries create one order, and reuse of the key with a changed payload is rejected. A different customer or merchant cannot read or update the order, and an out-of-order transition creates no event. |
| P2 | Staff assign a ready order to an active driver. The assigned driver confirms pickup and delivery, and the customer's refreshed page shows the final state and every successful transition once. Competing valid assignments yield one delivery and one assignment event. Concurrent pickup submissions produce one pickup event. Inactive driver assignment, out-of-order delivery, and access by an unassigned driver are rejected. The delivered order and history survive a restart with the same database volume. |

Public registration, payment processing and payouts, geocoding and spatial queries, live updates, automatic dispatch, mobile apps, reviews, and analytics are outside P0–P2. [Source handout](ideas/doordash_like_app_handout.md)
