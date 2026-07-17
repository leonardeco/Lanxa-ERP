# Backlog técnico (sin Contador ni administración)

Trabajo que el equipo de desarrollo puede hacer **sin** reunión contable ni repartir usuarios.

## Hecho en este carril (2026-07-17+)

| Item | Entrega |
|---|---|
| Arranque con espacios en ruta (`MI PC`) | `start.bat` usa `/D` + certs relativos |
| Backup unificado | `backend/scripts/backup_auto.py` |
| Login auto ops | `ops/_login_chrome.cjs`, `abrir-login-chrome.ps1` |
| Preflight #7 + versiones | `preflight-entrega-7.py` compara API vs `config.ts` |
| Seguridad / readiness docs | `SEGURIDAD-LAN.md`, `PRODUCTION-READINESS-LAN.md` |
| Backup Postgres scripts | `backup_pg.py` / `restore_pg.py` |
| Diagnostico ampliado | motor BD, backups, clave Fernet |
| Gitignore creds login | `_login_cred.json`, copias locales |

## Aun codeable sin Contador (siguiente)

| Idea | Valor | Esfuerzo |
|---|---|---|
| `backup_auto` en tarea Windows (documentar / registrar) | Un solo job | Bajo |
| Endurecer E2E CI (#27) si flaquea | Menos ruido en PRs | Medio |
| Test de contrato health `version` en backend | Detecta drift release | Bajo |
| Revisar Dependabot / pip-audit en cada PR | Seguridad deps | Bajo (CI ya corre) |
| Unificacion FK Tercero (opcional, 14a) | Limpieza modelo | Medio-alto |
| Mejoras UX no bloqueantes (a11y, mensajes) | Calidad | Variable |

## Explicitamente fuera (negocio / Contador / admin)

- #1 PUC, #2 maestros, #3 costeo, #8 costo venta, #4 retenedores reales, #24 decision redondeo
- #7 repartir tarjetas, #33op rotar Superusuario, clave en gestor personal
- #20 token Alegra, #22 resolucion DIAN, #23 texto legal Habeas
- #18 nomina, cloud apply productivo
