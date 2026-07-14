# Roadmap maestro ERP — Pendientes + migración a SaaS/AWS (unificado)

- **Fecha:** 2026-07-14
- **Decisión base:** ADR `docs/hydraia/adr/0001-lan-monoempresa-a-saas-multitenant-aws.md`
- **Runbook AWS:** `docs/hydraia/plans/2026-07-14-migracion-aws-runbook.md`
- **Backlog táctico:** `PENDIENTES.md` (sigue siendo la fuente única de ítems)
- **Decisión de secuencia (usuario 2026-07-14):** **desplegar v0.3.0 en LAN a la empresa
  #1 ahora**, construir el SaaS en paralelo, y migrar esa empresa a la nube en la Fase 4
  del runbook.

Este documento **no reemplaza** `PENDIENTES.md`; lo **ordena en carriles paralelos** y
muestra cómo la migración a AWS **absorbe, asciende o deja en paralelo** cada pendiente.

---

## Cómo la migración cruza el backlog (mapeo clave)

| Efecto | Pendientes | Qué pasa |
|---|---|---|
| **Resuelve (desaparecen)** | #5 backups offsite · #21a staging · #33op secrets | RDS backups/PITR · ambiente CI/CD · Secrets Manager |
| **Asciende a obligatorio** | #12 locks · #12a race numeración · #10 drift Alembic | ECS Fargate = multi-worker real → dejan de ser "opcionales" |
| **Paralelo e independiente** | #1 PUC · #2 maestros · #3 costeo · #4 UVT (→ #8) | Los gatilla la contadora; no dependen de la infra |
| **Bloqueantes de lanzamiento SaaS** | #20/#22 DIAN e-factura · #23 Habeas Data · #24 redondeo | Operar legal con múltiples empresas los exige |
| **Candidato a DESCARTAR** | #21 Electron (.exe) | Con dirección web/SaaS, una app de escritorio pierde sentido — confirmar y sacar del backlog |

---

## Carril 0 — GO-LIVE LAN empresa #1 (AHORA, ~1–2 semanas) 🚦

Objetivo: la primera empresa operando en LAN con v0.3.0. Son los 🟠 operativos.

- **#6** desplegar v0.3.0 (`alembic upgrade head` obligatorio, `pip install`, rename
  `ACCESS_TOKEN_EXPIRE_*`, `alembic stamp` una vez, CA en PCs cliente).
- **#33op** definir `SEED_ADMIN_PASSWORD` en el `.env` del servidor + rotar la clave del
  admin tras el primer login.
- **#7** entregar `MANUAL-DE-USUARIO.md` a los 4 usuarios y cambio de clave inicial.
- **#7b** documentar vigencia del cert TLS local y cuándo regenerarlo.
- **#7a** calendarizar el drill de restore trimestral.
- **#27** revisar a mano el job E2E del CI en el release.

**Checkpoint:** empresa #1 usando el ERP en LAN, backup probado.

## Carril A — NEGOCIO / CONTADORA (paralelo, continuo) 👥

Objetivo: correctitud contable. Independiente de infra — **empujar desde el día 1**.

- **#1** validar mapeo PUC (doc `MAPEO-PUC-PARA-CONTADOR.md` listo).
- **#2** datos maestros reales (importador de inventario ya existe).
- **#3** método de costeo (promedio ponderado) → desbloquea **#8** asiento costo de venta.
- **#4** confirmar `UVT_VALOR` 2026 + flags `retiene_*`.

**Checkpoint:** #1–#4 confirmados por la contadora → implementar #8.

## Carril B — CONSTRUIR EL SaaS (paralelo al Carril 0, ~4–8 semanas) ☁️

Sigue el **runbook AWS** por fases, **incorporando los pendientes ascendidos**:

- **Fase 0** prereqs (cuenta AWS, IAM/MFA, **instalar Docker**, dominio).
- **Fase 1 — multi-tenancy** (lo más pesado, **hacer con Hydraia**): `tenant_id` + **RLS**
  + tests de aislamiento + pasar dev a Postgres. **Incluye #10 (drift Alembic), #12 y
  #12a (locks/numeración) — aquí ya son obligatorios.**
- **Fase 2** containerización (Dockerfiles ya existen).
- **Fase 3** VPC + RDS + Secrets Manager + ECR (**absorbe #5 y #33op**).
- **Fase 4** migrar datos SQLite→RDS (incluye migrar a la empresa #1 desde LAN).
- **Fase 5** ECS Fargate + ALB + HTTPS + dominio.
- **Fase 6** hostear frontend estático (S3+CloudFront, **sin tocar código**).
- **Fase 7** CloudWatch + backups + CI/CD (**absorbe #21a staging**).
- **Fase 8** onboarding multi-empresa.

**Checkpoint duro:** no ir a producción cloud sin los tests de aislamiento (Fase 1) verdes.

## Carril C — CUMPLIMIENTO LEGAL (antes del lanzamiento SaaS público) ⚖️

- **#20/#22** facturación electrónica DIAN (cuenta/token Alegra real + resolución de
  numeración) — **bloqueante legal del lanzamiento**.
- **#23** Habeas Data (Ley 1581): aviso de privacidad + política de tratamiento.
- **#24** política de redondeo de retenciones validada con la contadora.

**Checkpoint:** e-factura DIAN operativa + Habeas Data publicado antes de abrir a clientes.

## Después / opcional 🔮

- **#18** RRHH y nómina (Fase 2 de producto).
- **#21b** multi-bodega (pregunta de negocio).
- **#21 Electron → descartar** si se confirma la dirección web/SaaS.

---

## Orden recomendado (vista de una línea)

**Carril 0 (LAN ya)** + **Carril A (contadora, paralelo)** arrancan **hoy**. En cuanto la
empresa #1 esté en LAN, el foco de desarrollo pasa al **Carril B (SaaS)** empezando por la
**Fase 1 multi-tenancy con Hydraia**. **Carril C (legal)** se cierra **antes** de abrir el
SaaS a clientes. El frontend no se toca en ningún carril.

> Regla: al completar un ítem, moverlo a `DOCUMENTACION.md` §13 y registrar la sesión en
> `BITACORA.md` (regla de mantenimiento vigente).
