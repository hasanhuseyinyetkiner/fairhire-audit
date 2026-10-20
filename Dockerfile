FROM python:3.12-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:0.9.18 /uv /uvx /bin/
WORKDIR /srv/app
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev --no-install-project
COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app
RUN uv sync --frozen --no-dev
ENV PATH="/srv/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    FAIRHIRE_APP_ENV=demo \
    FAIRHIRE_BIND_HOST=0.0.0.0 \
    FAIRHIRE_PORT=8104 \
    FAIRHIRE_ALLOW_NETWORK_BIND=true \
    FAIRHIRE_DATABASE_URL=postgresql+psycopg://fairhire:fairhire@db:5432/fairhire \
    FAIRHIRE_UPLOAD_DIR=/srv/data/uploads \
    FAIRHIRE_REPORT_DIR=/srv/data/reports \
    FAIRHIRE_SEED_DEMO=true \
    FAIRHIRE_CORS_ORIGINS=http://127.0.0.1:5104,http://localhost:5104
RUN mkdir -p /srv/data/uploads /srv/data/reports
EXPOSE 8104
CMD ["python", "-m", "app"]
