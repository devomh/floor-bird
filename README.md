# Doordish

Doordish is a Django and PostgreSQL delivery prototype. P1 adds customer checkout and merchant preparation to the catalog. [Prototype plan](docs/plan.md) · [Verification status](docs/status.md)

## Local development with uv

Install uv and use a local PostgreSQL database. The following commands start the database with Docker Compose. If you already run PostgreSQL in Podman, omit the Compose command and add `--env-file .env` after `--locked` in the `uv run` commands to load your connection settings. [Install uv](https://docs.astral.sh/uv/getting-started/installation/)

```sh
uv sync --locked
docker compose up --wait db
uv run --locked python manage.py migrate
uv run --locked python manage.py seed_demo
uv run --locked python manage.py seed_demo_accounts
uv run --locked python manage.py runserver
```

Open the catalog to see Verde Kitchen and its three products. Repeating the catalog seed preserves existing records. [Local catalog](http://127.0.0.1:8000/)

In another terminal, run the PostgreSQL-backed tests while the database container is running.

```sh
uv run --locked python manage.py test
```

If port 5432 is in use, export a free `POSTGRES_PORT` before starting the database and running the Django commands. The Django and PostgreSQL defaults are for local development.

## Run both services in Compose

```sh
docker compose up --wait db
docker compose build web
docker compose run --rm web python manage.py migrate
docker compose run --rm web python manage.py seed_demo
docker compose run --rm web python manage.py seed_demo_accounts
docker compose up -d web
```

Open [the catalog](http://127.0.0.1:8000/). Use `docker compose down` to stop the services and keep the PostgreSQL volume for the next run.

## Try the P1 order flow

1. Open the catalog and select **Order from Verde Kitchen**. Sign in as `demo-customer`, choose a quantity, enter a sample delivery address, and place the simulated order. Keep the order detail page open.
2. Open a separate browser profile or private window. Sign in as `demo-merchant`, open **Merchant orders**, accept the order, and mark it ready.
3. Refresh the customer’s order page to see **Ready** and the full status history.

`seed_demo_accounts` prints a generated password for each demo account on creation. Later runs preserve the passwords. Use Django’s `changepassword` command with the demo username if you need to reset one.
