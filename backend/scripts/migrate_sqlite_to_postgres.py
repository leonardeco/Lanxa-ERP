#!/usr/bin/env python3
"""
Fase 4 — Migración de datos SQLite (LAN) → PostgreSQL (RDS/local).

Uso (desde backend/ con venv):

  # 1) Destino con esquema al día:
  #    DATABASE_URL=postgresql+asyncpg://... alembic upgrade head

  # 2) Dry-run (solo cuenta filas):
  python scripts/migrate_sqlite_to_postgres.py \\
      --sqlite ./superozono.db \\
      --postgres postgresql://user:pass@host:5432/superozono_erp

  # 3) Migrar de verdad:
  python scripts/migrate_sqlite_to_postgres.py \\
      --sqlite ./superozono.db \\
      --postgres postgresql://user:pass@host:5432/superozono_erp \\
      --execute

Notas:
- Asigna tenant_id=1 a filas que no lo tengan (empresa LAN).
- No migra alembic_version (el destino ya tiene la cabeza vía Alembic).
- Trunca tablas destino en orden seguro si --wipe-dest (peligroso).
- Requiere: pip install psycopg2-binary (ya en requirements.txt).
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, unquote

# Orden padres → hijos (FK). Ajustar si se agregan tablas.
TABLE_ORDER: list[str] = [
    "tenants",
    "usuarios",
    "refresh_tokens",
    "plan_cuentas",
    "centros_costo",
    "periodos_contables",
    "parametros_tributarios",
    "parametros_nomina",
    "terceros",
    "productos",
    "clientes",
    "proveedores",
    "saldos_iniciales",
    "asientos_contables",
    "movimientos_asiento",
    "ventas_documentos",
    "ventas_detalles",
    "cotizaciones",
    "cotizaciones_detalles",
    "compras_documentos",
    "compras_detalles",
    "lotes",
    "movimientos_inventario",
    "cuentas_por_cobrar",
    "cuentas_por_pagar",
    "pagos",
    "devoluciones_venta",
    "devoluciones_venta_detalles",
    "devoluciones_compra",
    "devoluciones_compra_detalles",
    "document_sequences",
    "auditoria",
]

SKIP_TABLES = {"alembic_version", "sqlite_sequence"}

DEFAULT_TENANT_ID = 1


def _pg_connect(url: str):
    import psycopg2
    from psycopg2.extras import execute_batch

    # Acepta postgresql:// o postgresql+asyncpg://
    clean = url.replace("postgresql+asyncpg://", "postgresql://", 1)
    clean = clean.replace("postgresql+psycopg2://", "postgresql://", 1)
    conn = psycopg2.connect(clean)
    conn.autocommit = False
    return conn, execute_batch


def _sqlite_tables(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    return {r[0] for r in rows}


def _table_columns_sqlite(conn: sqlite3.Connection, table: str) -> list[str]:
    return [r[1] for r in conn.execute(f"PRAGMA table_info([{table}])")]


def _table_columns_pg(cur, table: str) -> list[str]:
    cur.execute(
        """
        SELECT column_name FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        ORDER BY ordinal_position
        """,
        (table,),
    )
    return [r[0] for r in cur.fetchall()]


def _count_sqlite(conn: sqlite3.Connection, table: str) -> int:
    return conn.execute(f"SELECT COUNT(*) FROM [{table}]").fetchone()[0]


def _count_pg(cur, table: str) -> int:
    cur.execute(f'SELECT COUNT(*) FROM "{table}"')
    return cur.fetchone()[0]


def migrate(
    sqlite_path: Path,
    postgres_url: str,
    *,
    execute: bool,
    wipe_dest: bool,
    tenant_id: int,
) -> int:
    if not sqlite_path.exists():
        print(f"ERROR: no existe SQLite {sqlite_path}", file=sys.stderr)
        return 2

    src = sqlite3.connect(str(sqlite_path))
    src.row_factory = sqlite3.Row
    src_tables = _sqlite_tables(src)

    print(f"Source: {sqlite_path}")
    print(f"Dest:   {urlparse(postgres_url.replace('+asyncpg', '')).hostname}")
    print(f"Mode:   {'EXECUTE' if execute else 'DRY-RUN'}")
    print()

    # Plan
    plan: list[tuple[str, int]] = []
    for t in TABLE_ORDER:
        if t in SKIP_TABLES or t not in src_tables:
            continue
        plan.append((t, _count_sqlite(src, t)))

    extra = src_tables - set(TABLE_ORDER) - SKIP_TABLES
    if extra:
        print("WARN tablas en SQLite no listadas en TABLE_ORDER:", sorted(extra))

    print("=== Conteos origen ===")
    total = 0
    for t, n in plan:
        print(f"  {t:35} {n:6}")
        total += n
    print(f"  {'TOTAL':35} {total:6}")
    print()

    if not execute:
        print("Dry-run OK. Añade --execute para copiar.")
        src.close()
        return 0

    pg, execute_batch = _pg_connect(postgres_url)
    cur = pg.cursor()

    try:
        if wipe_dest:
            print("WIPING destination tables (CASCADE order reverse)...")
            for t, _ in reversed(plan):
                cur.execute(f'TRUNCATE TABLE "{t}" RESTART IDENTITY CASCADE')
            pg.commit()

        # Desactivar triggers/FKs temporalmente no es trivial en PG;
        # insertamos en orden TABLE_ORDER.
        for t, n in plan:
            if n == 0:
                print(f"  skip empty {t}")
                continue

            s_cols = _table_columns_sqlite(src, t)
            p_cols = _table_columns_pg(cur, t)
            # Intersección en orden SQLite; omitir columnas solo-destino
            cols = [c for c in s_cols if c in p_cols]
            if not cols:
                print(f"  WARN {t}: no common columns, skip")
                continue

            need_tenant = "tenant_id" in p_cols and "tenant_id" not in cols
            if need_tenant:
                cols = cols + ["tenant_id"]

            rows = src.execute(
                f"SELECT {', '.join('[' + c + ']' for c in s_cols if c in p_cols)} FROM [{t}]"
            ).fetchall()

            values: list[tuple[Any, ...]] = []
            base_cols = [c for c in s_cols if c in p_cols]
            for row in rows:
                tup = tuple(row[c] for c in base_cols)
                if need_tenant:
                    tup = tup + (tenant_id,)
                values.append(tup)

            col_list = ", ".join(f'"{c}"' for c in cols)
            placeholders = ", ".join(["%s"] * len(cols))
            # ON CONFLICT DO NOTHING for re-runs on PK
            sql = f'INSERT INTO "{t}" ({col_list}) VALUES ({placeholders}) ON CONFLICT DO NOTHING'

            execute_batch(cur, sql, values, page_size=200)
            pg.commit()
            dest_n = _count_pg(cur, t)
            print(f"  {t:35} src={n:5} dest={dest_n:5}")

        # Reset sequences
        print()
        print("Resetting PostgreSQL sequences...")
        cur.execute(
            """
            SELECT table_name, column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND column_default LIKE 'nextval%'
            """
        )
        for table_name, column_name in cur.fetchall():
            cur.execute(
                f"""
                SELECT setval(
                  pg_get_serial_sequence('"{table_name}"', '{column_name}'),
                  COALESCE((SELECT MAX("{column_name}") FROM "{table_name}"), 1),
                  true
                )
                """
            )
        pg.commit()
        print("DONE.")
        return 0
    except Exception as exc:
        pg.rollback()
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    finally:
        cur.close()
        pg.close()
        src.close()


def main() -> None:
    p = argparse.ArgumentParser(description="Migrate Super Ozono SQLite → PostgreSQL")
    p.add_argument(
        "--sqlite",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "superozono.db",
    )
    p.add_argument(
        "--postgres",
        required=True,
        help="postgresql://user:pass@host:5432/dbname",
    )
    p.add_argument(
        "--execute",
        action="store_true",
        help="Realmente inserta (default: dry-run)",
    )
    p.add_argument(
        "--wipe-dest",
        action="store_true",
        help="TRUNCATE todas las tablas destino antes de copiar (destructivo)",
    )
    p.add_argument(
        "--tenant-id",
        type=int,
        default=DEFAULT_TENANT_ID,
        help="tenant_id por defecto si la fila no lo trae (default 1)",
    )
    args = p.parse_args()
    raise SystemExit(
        migrate(
            args.sqlite,
            args.postgres,
            execute=args.execute,
            wipe_dest=args.wipe_dest,
            tenant_id=args.tenant_id,
        )
    )


if __name__ == "__main__":
    main()
