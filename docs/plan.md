# Implementation plan

Build a Django modular monolith and verify one complete delivery with synthetic data. Each prototype adds a boundary the previous one did not exercise. Finish its exit checks before starting the next prototype. The proposed behavior and verification cases are in the [prototype specification](specs.md), and implementation progress belongs in [status](status.md).

| Prototype | New capability | What it verifies |
| --- | --- | --- |
| P0 · Catalog read | Boot the app, migrate and seed PostgreSQL, and render a catalog page | A fresh environment can run the stack and serve persisted data over HTTP |
| P1 · Order and preparation | Place an order as a customer and advance it as a merchant | Module boundaries, role authorization, price snapshots, atomic writes, and checkout retries |
| P2 · Manual delivery | Assign a driver, confirm pickup and delivery, and show progress to the customer | The full lifecycle, concurrent updates, driver-level authorization, and recovery after restart |

## P0 · Catalog read

1. Scaffold one Django project with a `catalog` app. Run Django and PostgreSQL through Docker Compose, with a persistent database volume and documented setup commands.
2. Add migrations and a repeatable demo seed command for one merchant and its products. Render the catalog with Django templates. Add Bootstrap or HTMX only when the interface needs them.
3. Add a GitHub Actions check that applies migrations and runs the backend tests against PostgreSQL. Cover the catalog and the repeatable seed command.

**Exit check.** From a fresh checkout and an empty database, start the app, migrate, seed twice, and load the catalog in a browser. Verify the second seed creates no duplicate demo records, and confirm CI passes against PostgreSQL.

## P1 · Order and preparation

1. Add `accounts` and `orders` modules. Use Django session authentication and seeded customer and merchant accounts. Provide a minimal order form with quantities, a synthetic delivery address, and simulated payment.
2. Put checkout and merchant actions in the order module. Recalculate totals from the catalog, snapshot the order data, and commit order creation and its initial event together. Give each checkout attempt a customer-scoped submission key.
3. Build the customer's order detail and the merchant's order queue with standard web forms. Let the merchant accept the order and mark it ready. Write the lifecycle event in the same transaction as each state change.

**Exit check.** Place an order in a browser, accept it in a separate merchant session, and mark it ready. Verify price snapshots, repeated and concurrent checkout submissions, an invalid transition, and cross-account access restrictions with PostgreSQL-backed tests.

## P2 · Manual delivery

1. Add a `deliveries` module with one delivery per assigned order. Seed a staff account and a driver account for the demo. Staff use a protected web form to assign an active driver to a ready order. Django Admin can manage demo accounts and catalog records and inspect orders and events.
2. Give drivers a responsive page with their assigned deliveries and controls for pickup and completion. Show the current state and event history on the customer's order detail after a refresh.
3. Run PostgreSQL-backed integration tests for competing assignments and state changes, including how stale requests are handled. Run the full browser scenario with separate customer, merchant, staff, and driver sessions.

**Exit check.** Complete the browser scenario from catalog to delivery. Confirm that simultaneous assignments produce one delivery and one assignment event, that another driver cannot read or update it, and that the order and its history survive an app and database restart using the same volume.

## Architecture review

Review the repeatable P0–P2 results, CI output, browser walkthrough, and concurrency and authorization tests. Record supporting evidence and the decision in [status](status.md). Proceed to feature work after these checks pass. If a check fails, fix the relevant prototype and rerun it before expanding scope.

After the review, choose the next prototype based on the capability the project needs most. The handout's next candidates are delivery zones and proximity queries with PostGIS, or a small Django REST Framework API exercised by an Expo driver app. Give the chosen capability a measurable exit check before implementation. Live tracking, automatic dispatch, marketplace payments, notifications, analytics, and deployment scaling remain future work. Keep the Django modules and shared PostgreSQL database unless an observed operational constraint justifies a change. [Source handout](ideas/doordash_like_app_handout.md)
