#!/bin/sh
# Arranque del backend en contenedor:
# 1) espera a Postgres (si DATABASE_URL es postgresql)
# 2) alembic upgrade head
# 3) exec del CMD (uvicorn)

set -e

echo "[entrypoint] Super Ozono API starting..."

if echo "${DATABASE_URL:-}" | grep -q "postgresql"; then
  echo "[entrypoint] Waiting for PostgreSQL..."
  python - <<'PY'
import os, sys, time
from urllib.parse import urlparse

url = os.environ.get("DATABASE_URL", "")
# postgresql+asyncpg://user:pass@host:5432/db → host/port
u = urlparse(url.replace("postgresql+asyncpg://", "postgresql://", 1)
               .replace("postgresql+psycopg2://", "postgresql://", 1))
host = u.hostname or "db"
port = u.port or 5432

import socket
deadline = time.time() + 60
while time.time() < deadline:
    try:
        with socket.create_connection((host, port), timeout=2):
            print(f"[entrypoint] Postgres reachable at {host}:{port}")
            sys.exit(0)
    except OSError:
        time.sleep(1)
print(f"[entrypoint] ERROR: Postgres not reachable at {host}:{port}", file=sys.stderr)
sys.exit(1)
PY

  echo "[entrypoint] Running alembic upgrade head..."
  alembic upgrade head
else
  echo "[entrypoint] DATABASE_URL is not PostgreSQL — skipping wait/migrate"
fi

echo "[entrypoint] exec: $*"
exec "$@"
