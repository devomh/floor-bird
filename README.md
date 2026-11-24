# Doordish

P0 is a read-only catalog served by Django and backed by PostgreSQL. See the [prototype plan](docs/plan.md) and [verification status](docs/status.md).

## Local development with uv

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) and Docker with the Compose plugin. From the repository root, run these commands.

```sh
uv sync --locked
docker compose up --wait db
uv run --locked python manage.py migrate
uv run --locked python manage.py seed_demo
uv run --locked python manage.py seed_demo
uv run --locked python manage.py runserver
```

Open [the catalog](http://127.0.0.1:8000/) to see Verde Kitchen and its three products. The first seed on an empty database adds three products. The second adds zero and preserves existing records.

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
docker compose run --rm web python manage.py seed_demo
docker compose up -d web
```

Open [the catalog](http://127.0.0.1:8000/). Use `docker compose down` to stop the services and keep the PostgreSQL volume for the next run.
