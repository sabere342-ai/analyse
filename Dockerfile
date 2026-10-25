FROM node:24.19.0-bookworm-slim AS frontend
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --ignore-scripts
COPY frontend/ ./
RUN npm run build

FROM python:3.12.14-slim-trixie AS python-build
WORKDIR /app
RUN pip install --no-cache-dir uv==0.12.23
COPY pyproject.toml uv.lock ./
COPY madrid/ madrid/
RUN uv sync --frozen --no-dev

FROM python:3.12.14-slim-trixie
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0 fontconfig fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --uid 10001 --create-home madrid \
    && install -d -o madrid -g madrid -m 700 /data /app/.cache
WORKDIR /app
COPY --from=python-build --chown=madrid:madrid /app/.venv /app/.venv
COPY --chown=madrid:madrid madrid/ madrid/
COPY --chown=madrid:madrid migrations/ migrations/
COPY --chown=madrid:madrid alembic.ini ./
COPY --from=frontend --chown=madrid:madrid /build/frontend/dist frontend/dist/
ENV MADRID_DATA_DIR=/data MADRID_SECURE_COOKIE=1 XDG_CACHE_HOME=/app/.cache PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
USER madrid
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s CMD ["/app/.venv/bin/python", "-c", "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PORT','8000')+'/api/health',timeout=4)"]
CMD ["sh", "-c", "exec /app/.venv/bin/uvicorn madrid.app:create_app --factory --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --no-proxy-headers"]
