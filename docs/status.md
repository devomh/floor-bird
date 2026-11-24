# Implementation status

**Current state.** P1 is implemented and verified locally. The updated GitHub Actions workflow is ready for its next hosted run.

| Deliverable | Status | Evidence |
| --- | --- | --- |
| Prototype roadmap | Drafted | [Implementation plan](plan.md) |
| Prototype behavior and acceptance cases | Drafted | [Specification](specs.md) |
| P0 · Catalog read | Locally verified | Catalog and PostgreSQL checks passed. The first hosted run passed tests and seeding, then hit a startup connection reset. The retry fix awaits hosted verification. |
| P1 · Order and preparation | Locally verified | All 15 tests passed against PostgreSQL. Chrome verified the two-role walkthrough, and the Podman image upgraded a P0 database in place. |
| P2 · Manual delivery | Not started | Pending end-to-end walkthrough, concurrency and access checks, and restart verification |
| Architecture review | Pending | Requires P0–P2 results and a recorded decision |

## Next milestone

Record a passing hosted run with the HTTP retry fix and P1 tests before starting P2. [Setup instructions](../README.md) · [GitHub Actions workflow](../.github/workflows/p0.yml)

## Verification log

| Date | Prototype | Outcome |
| --- | --- | --- |
| 2026-11-23 | P0 | Created the Python 3.13 environment with uv and verified the resulting lockfile. |
| 2026-11-23 | P0 | Applied migrations to an empty PostgreSQL 18.6 database. `seed_demo` added three products on the first run and zero on the second. All three Django tests passed. |
| 2026-11-23 | P0 | Loaded the catalog in headless Chrome and confirmed it displayed Verde Kitchen and the three persisted products with their prices. |
| 2026-11-23 | P0 | `docker compose config` passed with the standalone Compose CLI. A Docker daemon and GitHub remote were unavailable for the full Compose and hosted CI runs. |
| 2026-11-23 | P0 | The first hosted Compose run built the image, applied migrations, passed all three tests, and seeded twice. The HTTP smoke check hit a connection reset during web startup. Reproduced the reset locally and verified the revised retry handled it. [Hosted run](https://github.com/devomh/floor-bird/actions/runs/45300998939) |
| 2026-11-23 | P1 | Clean migrations and all 15 PostgreSQL-backed tests passed. Cases covered invalid checkout input, price snapshots, concurrent retries, rollback, and cross-account access. |
| 2026-11-23 | P1 | Chrome verified checkout in a customer session and acceptance and preparation in a separate merchant session. The refreshed customer page showed Placed → Accepted → Ready in order. |
| 2026-11-23 | P1 | Built the Podman image, applied P1 migrations to an isolated P0 database, confirmed the catalog seed added zero duplicate products, and reran all 15 tests from the container. |

## Architecture decision

Pending. Record the review date, supporting evidence, and either the next approved feature prototype or the fixes needed before feature work starts.
