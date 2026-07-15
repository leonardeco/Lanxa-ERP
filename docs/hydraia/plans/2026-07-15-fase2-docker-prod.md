# Plan — Fase 2: containerización producción (runbook AWS)

- **Goal:** imágenes backend/frontend listas para ECR/ECS; compose prod local.
- **Bloqueo en este PC:** Docker Desktop **no instalado** — no se pudo `compose up`.
  El artefacto queda versionado para cuando haya Docker o un CI con builders.

## Entregado

| Archivo | Cambio |
|---|---|
| `backend/Dockerfile` | Multi-stage, non-root `app`, sin `--reload`, healthcheck |
| `backend/docker/entrypoint.sh` | Espera PG + `alembic upgrade head` + exec |
| `backend/.dockerignore` | Excluye venv, .env, *.db, tests |
| `frontend/Dockerfile` | Multi-stage + nginx 1.27, ARG `VITE_API_URL` |
| `frontend/nginx.conf` | Proxy `/api`, `/health`, headers, cache assets |
| `frontend/.dockerignore` | node_modules, dist, e2e |
| `docker-compose.prod.yml` | Stack prod sin bind-mount de código |
| `.env.docker.example` | Plantilla de secretos para compose prod |

## Uso (cuando Docker esté instalado)

```bash
cp .env.docker.example .env.docker
# editar secretos

docker compose -f docker-compose.prod.yml --env-file .env.docker up -d --build

# smoke
curl -fsS http://localhost/health
curl -fsS http://localhost:8000/health
# UI: http://localhost/
```

## Dev compose

`docker-compose.yml` sigue siendo el stack de desarrollo (bind-mount, pgadmin).
No usar `--reload` en prod (eliminado del Dockerfile de backend).

## Siguiente (Fase 3 AWS)

VPC + RDS + Secrets Manager + ECR (IaC). Requiere cuenta AWS y Docker/CI.
