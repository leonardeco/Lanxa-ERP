# Runbook — Migración a AWS (SaaS multi-tenant, full AWS / ECS Fargate)

- **Deriva de:** ADR `docs/hydraia/adr/0001-lan-monoempresa-a-saas-multitenant-aws.md`
- **Decisión (usuario, 2026-07-14):** AWS completo desde el inicio, guiado por fases.
- **Fecha:** 2026-07-14
- **Regla de oro:** cada fase termina en un **checkpoint verificable**. No se avanza a la
  siguiente sin cumplirlo. El frontend **no se toca** (solo se hostea como estático).

> Estimación global honesta para un solo dev: **~4–8 semanas** de trabajo efectivo
> (la multi-tenancy y la infra AWS son lo pesado), repartidas para no bloquear la
> operación LAN de v0.3.0.

---

## Fase 0 — Prerrequisitos (local, ~1 día)

**Objetivo:** tener las herramientas y la cuenta listas, sin tocar código de la app.

1. Cuenta AWS con **usuario IAM** (nunca root para el día a día) + **MFA**; grupo con
   permisos de administrador acotado.
2. **AWS CLI** instalado y `aws configure` (perfil, región — sugerida `us-east-1`).
3. **Docker Desktop** instalado en tu máquina de desarrollo (el servidor LAN no lo
   necesita; ECS corre las imágenes). *Recordatorio: la instalación quedó pendiente en el
   ecosistema — este es el momento.*
4. Elegir el **dominio** (o subdominio) del SaaS y decidir el esquema multi-empresa:
   `empresa.tudominio.com` (subdominio por tenant) vs `app.tudominio.com/empresa`.

**Checkpoint:** `aws sts get-caller-identity` responde con tu cuenta; `docker run hello-world` funciona.

---

## Fase 1 — Multi-tenancy en el backend (local, ~1–2 semanas) ⚠️ LO MÁS PESADO

**Objetivo:** que un mismo despliegue sirva a N empresas con **aislamiento total de
datos**. Se hace **en local con Postgres**, antes de tocar AWS. Es el trabajo de mayor
riesgo (una fuga entre tenants es el peor fallo posible en un SaaS).

1. **Pasar dev a Postgres local**: levantar `docker compose up db` (ya tienes
   `postgres:16-alpine` en `docker-compose.yml`), apuntar `DATABASE_URL` a él, correr
   `alembic upgrade head` y **los 285 tests** contra Postgres. Reconciliar el drift de
   Alembic documentado (ver PENDIENTES #10).
2. **Modelo `Tenant`/`Empresa`** + columna `tenant_id` (FK) en todas las tablas de datos
   de negocio. Migración Alembic.
3. **Resolución de tenant por request**: middleware que deduce la empresa del **subdominio**
   o de un **claim `tenant_id` en el JWT**, y la fija en el contexto de la sesión.
4. **Aislamiento con Row-Level Security (RLS)** en Postgres: políticas que filtran por
   `tenant_id` usando una variable de sesión (`SET app.tenant_id = ...` por conexión), de
   modo que *ninguna query pueda ver datos de otra empresa aunque olvides el `WHERE`*.
5. **Auth con alcance de tenant**: el login resuelve la empresa; los roles existentes
   (Admin/Contador/etc.) pasan a ser **por empresa**.
6. **Tests de aislamiento** (nuevos, obligatorios): crear 2 tenants, datos en cada uno, y
   afirmar que las queries de uno **nunca** devuelven filas del otro.

**Checkpoint:** los 285 tests verdes en Postgres + los tests de aislamiento cross-tenant
pasan. Sin esto, NO se sube a la nube.

> Esta fase se debe construir con el pipeline **Hydraia** (`/hydraia:feature` o
> `/hydraia:architect`), no a mano — toca todos los modelos y es sensible a seguridad.

---

## Fase 2 — Containerización lista para producción (local, ~2–3 días)

**Objetivo:** una imagen del backend reproducible y delgada.

1. Revisar/endurecer `backend/Dockerfile` (multi-stage, usuario no-root, `pip install`
   de `requirements.txt`, `alembic upgrade head` como paso de arranque o job aparte).
2. `.dockerignore` (excluir venv, tests, `*.db`, `.env`).
3. Probar el stack completo localmente: `docker compose up` (backend + db + redis) y correr
   un smoke + los tests dentro del contenedor.
4. Build de la imagen de producción y prueba local apuntando a la Postgres del compose.

**Checkpoint:** `docker compose up` levanta backend+db+redis y el login responde 200; la
imagen del backend arranca y sirve `/docs`.

---

## Fase 3 — Fundamentos AWS: red + datos (~3–5 días)

**Objetivo:** la infra base donde vivirán la BD y el cómputo. **Recomendado: IaC**
(Terraform o AWS CDK) para que sea reproducible y versionado, no clicks en la consola.

1. **VPC** con 2 subredes públicas (ALB) y 2 privadas (RDS + tareas ECS) en 2 AZs;
   Internet Gateway; NAT Gateway (o VPC endpoints) para salida de las tareas privadas.
2. **RDS PostgreSQL** (empezar `db.t4g.micro/small`, Multi-AZ opcional) en las subredes
   privadas; **security group** que solo acepta desde el SG del backend; TLS forzado.
3. **Secrets Manager**: credenciales de la BD; **SSM Parameter Store**: config no secreta.
4. **ECR**: repositorio para la imagen del backend.

**Checkpoint:** puedes conectarte a RDS **solo** desde dentro de la VPC (un bastión o
`aws rds` temporal), nunca desde internet abierto; `ecr` acepta un `docker push`.

---

## Fase 4 — Migración de datos SQLite → RDS Postgres (~1–3 días)

**Objetivo:** llevar los datos reales (una vez exista la primera empresa) sin pérdida.

1. Congelar escrituras en la BD origen (ventana de mantenimiento).
2. Migrar con **pgloader** (SQLite→Postgres) o un script propio; cuidar tipos
   (booleanos, fechas, `Numeric`/decimales, autoincrement).
3. **Asignar `tenant_id`** a los datos existentes (la primera empresa).
4. `alembic stamp` + `alembic upgrade head` para dejar el esquema en la cabeza de la cadena.
5. Verificar integridad: conteos por tabla, cuadre contable (P&L/Balance), y un recorrido
   funcional.

**Checkpoint:** conteos origen == destino y el "✓ Cuadrado" del Balance sigue verde en RDS.

---

## Fase 5 — Cómputo: ECS Fargate + ALB + HTTPS (~3–5 días)

**Objetivo:** el backend corriendo y accesible por HTTPS con dominio.

1. **Push** de la imagen a ECR.
2. **ECS cluster** + **task definition** (Fargate): la tarea lee las credenciales desde
   Secrets Manager, corre `uvicorn`; una task/one-off para `alembic upgrade head`.
3. **ALB** + target group + health check (`/health` o `/docs`); **ACM** (certificado TLS)
   + **Route 53** (dominio); listener 443 → servicio ECS.
4. **CORS/orígenes**: `CORS_ORIGINS` del backend apunta al dominio del frontend.
5. Escalado: empezar con 1–2 tareas; autoscaling por CPU más adelante.

**Checkpoint:** `https://api.tudominio.com/docs` responde y el login funciona contra RDS.

---

## Fase 6 — Hosting del frontend (estático, sin tocar código) (~1 día)

**Objetivo:** servir el SPA existente. **El código del frontend no cambia.**

1. `npm run build` (Vite → `dist/`) con `VITE_API_URL=https://api.tudominio.com/api`.
2. Subir `dist/` a **S3**; **CloudFront** delante (HTTPS, dominio `app.tudominio.com`,
   fallback SPA a `index.html`).
3. Verificar el flujo completo login → vistas contra el backend en ECS.

**Checkpoint:** un navegador externo (fuera de la LAN) entra a `app.tudominio.com`,
inicia sesión y opera.

---

## Fase 7 — Observabilidad, backups y CI/CD (~3–5 días)

1. **CloudWatch**: logs de ECS, métricas y **alarmas** (5xx del ALB, CPU/errores).
2. **RDS**: backups automáticos + PITR verificados; snapshot manual antes de cada release.
3. **CI/CD** (GitHub Actions): en merge a `main` → build imagen → push ECR → update del
   servicio ECS (rolling). Migraciones como paso controlado.
4. Runbook de **rollback** (versión anterior de la task definition + snapshot RDS).

**Checkpoint:** un push a `main` despliega solo; una alarma llega a tu correo.

---

## Fase 8 — Onboarding multi-empresa (~2–3 días)

1. Alta de un **tenant** nuevo (empresa) con su admin, subdominio/claim y seeds base.
2. (Opcional) reutilizar el **seeder demo** para poblar un tenant de prueba y medir UI.
3. Documentar el proceso de alta para las siguientes 9+ empresas.

**Checkpoint:** dos empresas distintas operan en paralelo sin ver datos la una de la otra.

---

## Orden y dependencias (resumen)

`Fase 0 → 1 → 2` son **local** (haz la 1 con Hydraia). `Fase 3` puede empezar en paralelo
a la 2. `Fase 4` requiere 1+3. `Fase 5` requiere 2+3. `Fase 6` requiere 5. `Fase 7–8`
cierran. **No** desplegar a producción real hasta cerrar el checkpoint de aislamiento
(Fase 1).

## Riesgos principales

- **Fuga entre tenants** (Fase 1) — mitigar con RLS + tests de aislamiento obligatorios.
- **Costo AWS** subestimado — poner **billing alarms** desde la Fase 0.
- **Un solo dev** operando infra — por eso IaC (reproducible) y managed services (RDS,
  Fargate) en vez de auto-gestionar.
- No romper la operación LAN de v0.3.0 mientras se construye esto en paralelo.
