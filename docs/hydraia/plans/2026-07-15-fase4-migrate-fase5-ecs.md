# Plan — Fase 4 migración + Fase 5 ECS (borrador)

## Fase 4 — SQLite → Postgres

| Entrega | Path |
|---|---|
| Script | `backend/scripts/migrate_sqlite_to_postgres.py` |
| Guía | `backend/scripts/MIGRATE-SQLITE-POSTGRES.md` |

Dry-run sin Postgres remoto:

```bash
cd backend
python scripts/migrate_sqlite_to_postgres.py --sqlite ./superozono.db --postgres "postgresql://x:x@localhost/x"
# falla conexión si no hay PG; con PG local imprime conteos
```

## Fase 5 — ECS Fargate (código TF, default off)

| Entrega | Path |
|---|---|
| `infra/terraform/ecs.tf` | Cluster, ALB HTTP, task def, service |
| Flag | `enable_ecs = false` por defecto (no crea recursos ni costo) |

Activar:

```hcl
# terraform.tfvars
enable_ecs = true
api_image_tag = "v0.3.0"
```

Luego: push imagen a ECR → `terraform apply` → health en `alb_dns_name/health`.

HTTPS/ACM/dominio: siguiente iteración (listener 443 + certificado).
