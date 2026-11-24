FROM ghcr.io/astral-sh/uv:0.12.1 AS uv
FROM python:3.13-slim

COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH" \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONUNBUFFERED=1

COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev

COPY manage.py ./
COPY doordish ./doordish
COPY catalog ./catalog
COPY accounts ./accounts
COPY orders ./orders

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000", "--noreload"]
