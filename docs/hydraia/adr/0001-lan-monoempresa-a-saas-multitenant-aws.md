# 0001 — Transición de ERP LAN mono-empresa a SaaS multi-empresa en AWS con PostgreSQL

**Status:** accepted
**Date:** 2026-07-14

## Context

El ERP Super Ozono es hoy una aplicación **interna mono-empresa**:

- **Backend** FastAPI + SQLAlchemy 2.0 async + Alembic (10 migraciones). Ya soporta
  ambos dialectos (`app/core/database.py`); dependencias `asyncpg` y `psycopg2-binary`
  presentes. **~285 tests** verdes. Versión **v0.3.0 production-ready**.
- **Producción hoy corre en SQLite** (`DATABASE_URL=sqlite+aiosqlite:///./superozono.db`),
  no en PostgreSQL, aunque el `docker-compose.yml` sí define un servicio Postgres.
- **Despliegue** en LAN: 5 PCs (1 servidor + 4 clientes solo-browser), arranque por
  `start.bat` (uvicorn + vite en HTTPS con cert autofirmado para `192.168.1.47`).
  **Docker NO está instalado** en el servidor.
- **Frontend** React 19 + Vite (SPA, sin router, navegación por estado). Auth: access
  token en memoria + refresh en cookie HttpOnly.
- **Un solo desarrollador** (Leonardo) mantiene todo el ecosistema.

**Fuerza del cambio:** a corto plazo el producto deja de ser interno — se lanzará como
software usado por **≥10 empresas** simultáneamente. Eso exige aislamiento de datos por
empresa, acceso remoto (fuera de la LAN), y una BD/infra gestionada. El driver del
usuario ("rapidez y fluidez") **no** se resuelve con esta transición (la fluidez depende
de backend/queries/render, no del hosting ni del framework); el driver real y legítimo
es **multi-empresa + acceso remoto**.

**Supuestos (por confirmar; con su disparador de revisión):**
- Se asume **~10–50 empresas** en el horizonte cercano, no miles. *Revisar si el
  objetivo pasa a cientos/miles de tenants* → puede empujar hacia aislamiento más fuerte
  o sharding.
- Se asume presupuesto para una BD gestionada (RDS) y un cómputo pequeño en AWS.
  *Revisar si el costo mensual es un bloqueo* → alternativas más baratas (Lightsail,
  una sola VM).
- Se asume que la primera empresa se despliega **primero en LAN** con v0.3.0 para
  validar el producto antes de invertir en la nube.

## Decision

Adoptar, **como fase posterior al despliegue LAN de v0.3.0**, una transición deliberada
y por etapas hacia **SaaS multi-empresa en AWS**:

1. **Datos:** migrar de SQLite a **PostgreSQL gestionado en Amazon RDS** (Postgres, no
   Aurora en la primera etapa). El código ya es compatible; el trabajo real es la
   migración de datos SQLite→Postgres y la reconciliación del drift de Alembic ya
   documentado.
2. **Aislamiento multi-tenant:** **Row-Level Security (RLS) con `tenant_id`** en una
   sola base de datos, como modelo de partida.
3. **Cómputo del backend:** contenedores en **Amazon ECS sobre Fargate** (serverless,
   sin gestionar EC2), tras un **Application Load Balancer** con HTTPS (**ACM** + dominio
   en **Route 53**). Los `Dockerfile` de backend y frontend **ya existen** y
   `docker-compose.yml` ya modela Postgres/Redis, así que la containerización es un punto
   de partida, no trabajo desde cero. Imagen en **ECR**. *(Decisión del usuario 2026-07-14:
   ir a AWS completo desde el inicio, guiado por fases; se documenta la mayor carga
   operativa como consecuencia asumida.)*
4. **Red y secretos:** **VPC** con subredes privadas (RDS + tareas ECS) y públicas (ALB);
   RDS accesible solo desde el security group del backend; **TLS a la BD**; credenciales y
   config sensible en **AWS Secrets Manager / SSM Parameter Store** (no en `.env` plano);
   backups automáticos + PITR de RDS; logs y alarmas en **CloudWatch**.
5. **Frontend:** el código **no se toca** (confirmado por el usuario) — el SPA de Vite se
   **hostea como estático en S3 + CloudFront** (HTTPS/dominio), apuntando su
   `VITE_API_URL` al ALB del backend. La eventual migración a Next.js es **ortogonal** y se
   **pospone** (ADR futuro si se decide).

Cada elección táctica fina (servicio de cómputo definitivo, Aurora vs RDS, estrategia de
migraciones por tenant) que resulte costosa de revertir tendrá **su propio ADR** cuando
se tome.

## Alternatives considered

**Almacenamiento**
- **Seguir en SQLite (incluso en un archivo compartido/servidor):** rechazado — no
  soporta concurrencia real de múltiples escritores ni multi-tenant serio; sin backups
  gestionados ni acceso remoto seguro.
- **Aurora PostgreSQL desde el día 1:** rechazado por ahora — más caro y complejo que RDS
  Postgres para ~10 tenants; se puede migrar a Aurora luego si la escala lo exige
  (disparador: > cientos de tenants o necesidad de réplicas de lectura).
- **BD auto-gestionada (Postgres en una EC2 propia):** rechazado — traslada al único dev
  la carga de backups, parches y HA; RDS lo absorbe.

**Modelo multi-tenant**
- **Schema-por-empresa (un schema Postgres por tenant):** rechazado como partida —
  aislamiento más fuerte pero multiplica la complejidad de migraciones (correr Alembic ×N
  schemas) y de conexiones; se reconsidera si un cliente exige aislamiento físico
  (disparador: requisito contractual/regulatorio de segregación).
- **Base-de-datos-por-empresa:** rechazado — máximo aislamiento pero máximo costo y
  operación (N instancias/DBs, N backups); solo justificable para clientes enterprise
  puntuales.
- **RLS con `tenant_id` (elegido):** un esquema, una migración, políticas RLS que filtran
  por tenant. Mejor relación aislamiento/operación para un solo dev y ~10–50 tenants.
  Costo: **toca todos los modelos y queries** (agregar `tenant_id` + FK + políticas) y
  exige disciplina para que ninguna query escape el filtro.

**Cómputo del backend**
- **ECS sobre Fargate (elegido):** contenedores serverless tras ALB; sin gestionar
  servidores, escala horizontal, encaja con los `Dockerfile` ya existentes. Costo: mayor
  complejidad inicial (VPC, task definitions, ALB, ECR) y carga operativa — asumida
  explícitamente por decisión del usuario.
- **Dejar el backend en el PC LAN y solo la BD en AWS:** rechazado — cada query cruzaría
  internet → la app se vuelve **más lenta** y expone la BD; contradice el objetivo.
- **VM simple (Lightsail/EC2 con uvicorn tras Nginx):** rechazado a favor de Fargate —
  menos infra y más barato, pero deja parches/HA/escala al único dev; el usuario prefirió
  el camino gestionado de AWS. *Revisar si el costo de Fargate resulta un bloqueo* →
  degradar a esta opción.
- **Elastic Beanstalk / App Runner:** alternativas gestionadas más simples que ECS;
  rechazadas por menos control y por preferir el estándar ECS/Fargate del objetivo.

**Frontend**
- **Migrar a Next.js como parte de este cambio:** rechazado/pospuesto — no aporta a
  multi-tenancy ni a "rapidez" (es una SPA autenticada con backend propio); acoplarlo aquí
  aumenta riesgo y alcance. Se decidirá aparte, con motivo propio (marketing/signup con
  SEO, subdominios por tenant, o unificación con las apps Next del ecosistema).

## Consequences

- **Bueno:** acceso remoto real para múltiples empresas; BD gestionada con backups/PITR y
  concurrencia; base para escalar; secretos fuera del repo; el código ya está listo para
  Postgres (cambio de conexión + `alembic upgrade head`).
- **Bueno:** desacopla la decisión de infra de la del frontend — se puede avanzar en AWS
  sin tocar React/Vite.
- **Malo:** **RLS con `tenant_id` obliga a modificar todos los modelos y queries** y a
  auditar que ninguna consulta omita el filtro (riesgo de fuga entre tenants — el fallo
  más grave posible en un SaaS). Requiere pruebas específicas de aislamiento.
- **Malo:** migración SQLite→Postgres no trivial (tipos, fechas, autoincrement, decimales)
  + reconciliar el drift de Alembic existente; ~1–3 días con pruebas.
- **Malo:** nuevo costo mensual recurrente (RDS + cómputo) y **nueva carga operativa** para
  un solo dev (VPC, security groups, TLS, monitoreo, rotación de secretos, actualizaciones).
- **Malo:** el despliegue deja de ser `start.bat`; hay que construir un pipeline de deploy
  y un plan de rollback distintos a los actuales.
- **Neutro/Riesgo:** hacer esto **antes** de validar el producto con la primera empresa en
  LAN sería invertir en escala antes de tener tracción — por eso la decisión es explícita
  en secuenciar el despliegue LAN primero.
