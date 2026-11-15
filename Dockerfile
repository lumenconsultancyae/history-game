# syntax=docker/dockerfile:1
FROM node:22-alpine AS frontend-builder
WORKDIR /frontend
COPY frontend/package*.json ./
RUN --mount=type=cache,target=/root/.npm \
    npm install
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim AS backend-builder
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
COPY pyproject.toml README.md ./
COPY src/ ./src/
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip && \
    pip install --prefix=/install .

FROM python:3.12-slim AS runtime
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    HISTORY_GAME_DATABASE_URL="sqlite+aiosqlite:////app/data/history_game.db" \
    HISTORY_GAME_STATIC_DIR="/app/frontend/dist"

RUN groupadd --gid 10001 appgroup && \
    useradd --uid 10001 --gid appgroup --shell /sbin/nologin --create-home appuser && \
    mkdir -p /app/data /app/frontend/dist && \
    chown -R appuser:appgroup /app

COPY --from=backend-builder /install /usr/local
COPY --chown=appuser:appgroup pyproject.toml alembic.ini ./
COPY --chown=appuser:appgroup migrations/ ./migrations/
COPY --chown=appuser:appgroup src/ ./src/
COPY --from=frontend-builder --chown=appuser:appgroup /frontend/dist /app/frontend/dist

USER appuser
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
    CMD ["python3", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=2)"]

ENTRYPOINT ["uvicorn", "history_game.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
