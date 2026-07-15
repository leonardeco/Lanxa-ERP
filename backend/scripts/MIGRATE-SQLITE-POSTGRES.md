# Migración SQLite (LAN) → PostgreSQL (Fase 4)

## Cuándo usarlo

- Vas a poner la empresa #1 en **RDS Postgres** (o Postgres local/Docker).
- Ya corriste `alembic upgrade head` en el destino (esquema al día, incl. tenants/RLS).

## Prerrequisitos

1. Backup cifrado del SQLite LAN (`scripts/backup_db.py`).
2. Destino Postgres accesible (VPN/bastion si es RDS).
3. Variables de conexión a mano (no commitear passwords).

## Pasos

### 1. Esquema en destino

```bash
cd backend
export DATABASE_URL="postgresql+asyncpg://USER:PASS@HOST:5432/superozono_erp"
alembic upgrade head
```

### 2. Dry-run (solo conteos)

```bash
python scripts/migrate_sqlite_to_postgres.py \
  --sqlite ./superozono.db \
  --postgres "postgresql://USER:PASS@HOST:5432/superozono_erp"
```

### 3. Migración real

```bash
# Opcional: vaciar destino si reintentas
python scripts/migrate_sqlite_to_postgres.py \
  --sqlite ./superozono.db \
  --postgres "postgresql://USER:PASS@HOST:5432/superozono_erp" \
  --wipe-dest \
  --execute
```

### 4. Verificación

- Conteos origen ≈ destino (el script los imprime).
- Login con admin.
- Balance / una venta de prueba.
- `SELECT count(*) FROM productos WHERE tenant_id = 1;`

### 5. Cutover

1. Ventana de mantenimiento: `stop.bat` en LAN.
2. Migración final `--execute`.
3. Apuntar app (ECS o compose) a `DATABASE_URL` de Postgres.
4. Smoke + comunicar a usuarios.

## Comportamiento

| Tema | Detalle |
|---|---|
| `tenant_id` | Si falta en origen, se fuerza a `1` (Super Ozono) |
| `alembic_version` | No se copia |
| Re-runs | `ON CONFLICT DO NOTHING` (no duplica PK) |
| Secuencias | Se resetean al MAX post-carga |

## Rollback

Restaurar SQLite desde backup cifrado y volver a `start.bat`.  
RDS: snapshot automático de 7 días (Terraform Fase 3).
