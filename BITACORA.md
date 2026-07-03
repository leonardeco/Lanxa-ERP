# Bitácora de sesiones — Super Ozono ERP

Registro acumulado de sesiones de trabajo. En vez de crear un archivo `SESION-AAAA-MM-DD.md` por cada sesión, las nuevas entradas se agregan al final de este mismo archivo.

---

## Sesión — 16 de junio 2026

### Resumen

Se completaron dos módulos nuevos: **Compras & Proveedores** (completo, backend + frontend) y la integración de **pagos a proveedores** dentro del módulo de Cartera (CxP automática al confirmar compra, sincronización de `estado_pago`). Ambos fueron probados end-to-end y pusheados a GitHub.

### Lo que se hizo

**1. Módulo Compras & Proveedores (nuevo, desde cero)**

Backend (`backend/app/modules/compras/`): `models.py` (`Proveedor`, `CompraDocumento`, `CompraDetalle`), `schemas.py`, `router.py` (CRUD proveedores, CRUD compras, `/confirmar`, `/anular`, dashboard KPIs). Registrado en `main.py`. Autonumeración `SOG-CP-0001`, `SOG-CP-0002`, ...

Frontend: `comprasApi.ts`, `printCompra.ts` (impresión PDF), `ComprasView.tsx` con 4 pestañas (Dashboard, Proveedores, Compras, Nueva Compra). Registrado en `App.tsx` y `Sidebar.tsx`. Permisos: los 3 roles tienen acceso completo.

**2. Pagos a proveedores integrados en Cartera**

- `CuentaPorPagar` gana campo `compra_id` (FK lógica a `compras_documentos`).
- Al confirmar una compra se crea automáticamente la CxP correspondiente (idempotente).
- Al abonar una CxP con `compra_id`, se sincroniza `CompraDocumento.estado_pago` (Pagado/Parcial). Al anular, se marca `estado_pago = "Anulado"`.
- Frontend: columna "Origen" (Compra/Manual) en la tabla de CxP, botón "Pagar" para CxP de proveedores.

### Commit de esta sesión

```
7652ce1  feat(compras+cartera): modulo Compras & Proveedores con pagos integrados a CxP
```

---

## Sesión — 17 de junio 2026

### Resumen

Sesión de verificación y preparación para mover el ERP a un PC nuevo, que pasaría a ser el **PC servidor**. Se corrigió documentación desincronizada, un bug real de permisos, y se rotaron credenciales sensibles.

### Lo que se hizo

1. **`DOCUMENTACION.md` sincronizado con el código real** — le faltaba el módulo Compras completo en 4 secciones (estructura, modelos, endpoints, vistas) y en la tabla de roles. Se sincronizó todo + roadmap + fecha.
2. **Bug real corregido: rol Auxiliar bloqueado en Compras** — `compras/router.py` protegía todos los endpoints con `AdminOrAdministradoraDep`, pero el frontend ya mostraba el módulo a Auxiliar (recibía 403 en todo). Se alineó con el patrón de `ventas/router.py`.
3. **`.gitignore` corregido + `backend/.env.servidor` creado** — el patrón `backend/.env.*` bloqueaba cualquier plantilla de entorno del backend; se cambió a `backend/.env.local` + `backend/.env.*.local`.
4. **Rotación de credenciales** — `SECRET_KEY` (dev y Docker), `POSTGRES_PASSWORD`, `PGADMIN_PASSWORD`. Decisión confirmada: el PC servidor corre en modo `start.bat` + SQLite (no Docker/PostgreSQL) por ahora.
5. **QA**: se instalaron `pytest`, `flake8`, `mypy` (backend) y se corrió `ESLint` (frontend); primeros tests unitarios en verde.

### Commits de esta sesión

```
4f502eb  docs: sincronizar DOCUMENTACION.md con el modulo Compras & Proveedores
8247a3b  fix(compras): permitir rol Auxiliar en lectura/creacion/confirmacion
df4ab3d  fix(env): permitir templates backend/.env.* en git y agregar .env.servidor
10b9151  Implementar entorno de pruebas unitarias y análisis estático
```

### Pendiente que quedó al llegar al PC servidor (resuelto el 18 de junio — ver abajo)

1. Averiguar la IP del PC servidor (`ipconfig`), copiar `backend/.env.servidor` → `backend/.env` y `frontend/.env.servidor` → `frontend/.env` con la IP real y una `SECRET_KEY` nueva.
2. Ejecutar `start.bat` y verificar acceso desde otro dispositivo de la LAN.

---

## Sesión — 18 de junio 2026

### Resumen

Auditoría completa del `README.md`, fix de una incompatibilidad real de versiones en el backend, rediseño de la pantalla de login con el logo de la empresa, y creación de un acceso directo de escritorio instalable en cualquier PC servidor. Todo quedó commiteado y pusheado a GitHub. Backend y frontend quedaron corriendo en esta máquina (PC servidor, `192.168.1.81`), lanzados vía el acceso directo nuevo — confirmando que el traslado al PC servidor planeado el 17 ya se completó.

### Lo que se hizo

**1. Auditoría y parcheo de `README.md`**

Checklist de 38 ítems (estructura, variables de entorno, arquitectura, contrato de API, seguridad): 14 ✅ / 13 ⚠️ / 11 ❌ (cobertura completa 37%). Parches aplicados directamente:

- Prerrequisito `Git`, referencia a `.env.example`, nota sobre que no hay migraciones reales (Alembic en `requirements.txt` sin inicializar — el esquema se crea con `Base.metadata.create_all()`).
- Tabla de Variables de entorno: agregada `CORS_ORIGINS` (existía en código pero no documentada ni en `.env.example`), longitud mínima de `SECRET_KEY`.
- Nueva sección **Modelo de datos**: tabla de entidades con tipos/restricciones, con notas honestas de que los IDs son `Integer autoincrement` (no UUID) y `rol` es `String(50)` libre sin `CHECK` constraint — deuda técnica real.
- Diagrama de arquitectura real (cliente → nginx → FastAPI → Postgres/Redis), antes solo había árbol de carpetas.
- Tabla de niveles de acceso de la API, y aclaración de que no hay registro público por diseño (ERP interno, no SaaS).
- Nueva sección **Seguridad**: implementado (CORS sin wildcard, bcrypt, middleware 401, RBAC 403, ORM parametrizado, secretos fuera de git) vs. pendiente (JWT de 8h sin refresh tokens, sin rate limiting, sin TLS, sin backups automatizados).

Commit: `15d3229`

**2. Fix real: incompatibilidad `bcrypt` / `passlib`**

Warning en cada login: `(trapped) error reading bcrypt version`. Causa: `passlib==1.7.4` lee `bcrypt.__about__.__version__`, removido desde `bcrypt` 4.1.0. Se fijó `bcrypt==4.0.1` en `requirements.txt`. Verificado: warning desaparece, `pytest` sigue en verde (4/4).

Commit: `4651572`

**3. Rediseño de la pantalla de login con el logo de la empresa**

Se procesó una captura de pantalla del logo (210×190px, `Pictures/Screenshots`) con Pillow: flood-fill para quitar el fondo gris (preservando el texto blanco interior por conectividad), reescalado 4x con LANCZOS + unsharp mask para mayor nitidez al mostrarse en CSS. Guardado en `frontend/public/logo_ozono.png` (también arregló una referencia rota que ya existía en `index.html`).

Iteraciones (varias rondas de feedback): panel de marca a la derecha con fondo negro (`e5c5c19`) → mejora de nitidez (`b07a616`) → versión final: tarjeta centrada sin espacios negros, con logo pequeño arriba del título reemplazando el ícono genérico (`0528cae`).

Verificado en navegador real (Edge headless + capturas, ancho y angosto) y con login end-to-end usando Playwright (temporal, no quedó en el proyecto) — entra correctamente al Dashboard sin errores de consola.

**4. Acceso directo de escritorio (instalable en cualquier PC)**

`icon.ico` (multi-resolución 16–256px, lienzo cuadrado) generado desde el logo. `crear-acceso-escritorio.ps1` (usa `$PSScriptRoot`, sin rutas fijas) + `crear-acceso-escritorio.bat` (wrapper de doble clic) crean un acceso directo **"Super Ozono ERP"** en el escritorio, apuntando a `start.bat` con el ícono de la empresa. Probado con doble clic real — backend y frontend arrancaron, navegador se abrió solo. Documentado en `README.md` y `DOCUMENTACION.md` (hay que ejecutar el instalador una vez por cada PC servidor nuevo; el `.lnk` no es copiable porque apunta a una ruta absoluta).

Commit: `5c570ae`

**5. Monitoreo de salud (temporal, detenido al cierre)**

Chequeo automático cada 10 minutos (cron en memoria de la sesión) de `HTTP 200` en backend/frontend. Detenido a pedido del usuario al final de la sesión.

**6. Consolidación de notas de sesión**

`SESION-2026-06-16.md` y `SESION-2026-06-17.md` se fusionaron en este archivo (`BITACORA.md`) para no seguir creando un archivo nuevo por cada sesión.

### Commits de esta sesión

```
15d3229  docs: auditoria y parcheo de README — arquitectura, modelo de datos, API y seguridad
4651572  fix(backend): pin bcrypt a 4.0.1 para compatibilidad con passlib 1.7.4
e5c5c19  feat(login): panel de marca con logo de la empresa en pantalla de login
b07a616  fix(login): mejorar nitidez del logo en el panel de marca
5c570ae  feat: acceso directo de escritorio con logo para arrancar el ERP
0528cae  fix(login): volver a card centrada con logo pequeño en el header
```

### Estado al cierre

| Elemento | Estado |
|---|---|
| Código (git) | ✅ Limpio, todo commiteado y pusheado a `origin/main` |
| Backend (`:8000`) / Frontend (`:5173`) | ✅ Corriendo, lanzados vía acceso directo de escritorio |
| Acceso directo "Super Ozono ERP" | ✅ Creado y probado en esta máquina |
| `logo_ozono.png` / `icon.ico` | ✅ Generados desde una captura de baja resolución — mejorables si aparece el archivo original en alta calidad |
| Chequeo automático de salud | ⏸️ Detenido |

### Pendientes / riesgos conocidos

1. ~~Sin rate limiting en login (fuerza bruta).~~ → resuelto el 19 de junio, ver abajo.
2. ~~Sin refresh tokens — JWT de 8h en `localStorage`, sin revocación.~~ → resuelto el 19 de junio, ver abajo (de paso también se bajó el TTL del access token a 1h).
3. ~~Sin backups automatizados de PostgreSQL.~~ → resuelto el 19 de junio para SQLite (que es lo que corre en producción), ver abajo. Queda como riesgo menor que el backup esté en el mismo PC.
4. ~~Sin TLS — aceptable temporalmente por ser LAN cerrada.~~ → resuelto el 19 de junio con HTTPS + CA local, ver sesión más abajo. Queda pendiente instalar la CA en los 4 PCs cliente.
5. ~~`rol` sin constraint en BD~~ → resuelto el 19 de junio, ver sesión más abajo. IDs secuenciales (no UUID) sigue sin tocar — deuda técnica, no urgente en este contexto.
6. ~~Reset de contraseña por Admin (usuario sin acceso) — sugerido, no implementado, pendiente de aprobación.~~ → resuelto el 19 de junio, ver sesión más abajo.
7. Logo en mejor resolución si aparece el archivo original (no una captura de pantalla).

---

## Sesión — 19 de junio 2026

### Resumen

Se implementó rate limiting en el login para mitigar fuerza bruta — resuelve el pendiente #1 anotado al cierre de la sesión del 18 de junio.

### Lo que se hizo

**Rate limiting en `POST /api/login/access-token`**

- Librería `slowapi` (wrapper de `limits` para FastAPI/Starlette), agregada a `requirements.txt`.
- `backend/app/core/limiter.py` (nuevo): instancia compartida `Limiter(key_func=get_remote_address)` con storage **en memoria**. Decisión deliberada en vez de Redis: el PC servidor corre un solo proceso `uvicorn` vía `start.bat`, sin Docker, así que no hay beneficio real de un storage distribuido y sí se sumaría una dependencia operativa nueva.
- Límite: **5 intentos por minuto por IP**. Al superarlo, responde `429` con `{"error": "Rate limit exceeded: 5 per 1 minute"}`.
- Conectado en `main.py` (`app.state.limiter`, exception handler de `RateLimitExceeded`, `SlowAPIMiddleware`) y aplicado con `@limiter.limit("5/minute")` sobre el endpoint de login. *(`SlowAPIMiddleware` se quitó más tarde el mismo día — ver sesión de refresh tokens abajo.)*
- `tests/conftest.py`: limiter desactivado (`limiter.enabled = False`) durante los tests para que no afecte la suite.
- Fix incidental encontrado en el camino: `slowapi` autodetecta y lee un `.env` del directorio actual al instanciar `Limiter`; en Windows lo abre con el codec `cp1252` (no UTF-8) y crasheaba contra el `.env` real del proyecto (tiene tildes y guiones largos). Se neutralizó pasando `config_filename="slowapi_unused.env"` (nombre de archivo que no existe a propósito).
- Verificado: `pytest` 4/4 en verde, y prueba manual con 6 intentos seguidos de login con credenciales erróneas (5× `400`, 6to `429`).

El resto de los pendientes de la sesión del 18 de junio sigue igual (ver lista arriba).

### Commit de esta sesión

```
4a4b4a0  feat(seguridad): rate limiting en login (5 intentos/min por IP)
```

---

## Sesión — 19 de junio 2026 (continuación) — Refresh tokens

### Resumen

Se implementaron refresh tokens con rotación para el login — resuelve el pendiente #2 anotado al cierre de la sesión del 18 de junio. De paso se bajó el TTL del access token de 8h a 1h (otro pendiente de esa misma lista), viable porque ahora se renueva solo. En el camino se encontraron y corrigieron dos bugs reales (uno en el backend, otro en `start.bat`).

### Lo que se hizo

**1. Refresh tokens con rotación**

- Estrategia elegida (conversada con el usuario): **stateful con rotación**, no JWT stateless — se necesitaba poder revocar sesiones de verdad (logout real, no solo borrar el token del navegador), algo que un refresh token stateless no permite.
- `backend/app/modules/usuarios/models.py`: tabla nueva `refresh_tokens` (hash del token vía SHA-256, nunca el valor crudo — igual que las contraseñas).
- `backend/app/core/security.py`: `generate_refresh_token()` (token opaco aleatorio, no JWT), `hash_refresh_token()`, `refresh_token_expiry()`.
- `backend/app/modules/usuarios/router.py`: login ahora también deja una cookie `HttpOnly` (`refresh_token`, `Path=/api/login`, `SameSite=Strict`, `Secure=False` por no haber TLS todavía, 30 días). Nuevos endpoints `POST /login/refresh-token` (valida la cookie, **rota**: borra el token usado y emite uno nuevo — reusar uno ya rotado da `401`, eso es la detección de robo) y `POST /login/logout` (revoca en BD + limpia la cookie).
- `backend/app/core/config.py` + los 5 archivos `.env*`: `ACCESS_TOKEN_EXPIRE_HOURS` de `8` a `1`.
- `frontend/src/services/api.ts`: `withCredentials: true`; interceptor que, ante un `401`, llama a `/login/refresh-token` una vez y reintenta la request original con el access token nuevo.
- `frontend/src/contexts/AuthContext.tsx`: al cargar la app, si no hay access token vigente intenta renovarlo en silencio (cookie) antes de mandar al login; `logout()` ahora también revoca en el backend.
- 2 tests nuevos (`test_refresh_token_rotation`, `test_logout_revoca_refresh_token`) cubriendo la rotación y la revocación.

**2. Bug real encontrado: `SlowAPIMiddleware` rompía escrituras async a la BD**

Al escribir el primer test que hace un `INSERT` real via la API (el login ahora también crea una fila en `refresh_tokens`), saltó `sqlalchemy.exc.MissingGreenlet`. Causa: `BaseHTTPMiddleware` (la clase base de `SlowAPIMiddleware`, agregado en la sesión de rate limiting) no es compatible con el bridge de greenlet que usa SQLAlchemy async + `aiosqlite`. Como solo se usa el decorador `@limiter.limit()` por endpoint (sin `default_limits` globales), el middleware no hacía falta — se quitó de `main.py`. Ningún test anterior lo había detectado porque ninguno hacía un `INSERT` via HTTP todavía.

Segunda causa relacionada, en el código nuevo: se accedía a `user.id` *después* de `await session.commit()`; la sesión de tests expira los atributos al commitear (a diferencia de la sesión de producción, que tiene `expire_on_commit=False`). Se corrigió capturando `user_id = user.id` antes del commit, en ambos endpoints.

**3. Bug real encontrado: cookie del refresh token bloqueada por `SameSite` al abrir por `localhost`**

Verificado con Playwright en un navegador real (Chromium, instalado temporalmente, no quedó en el proyecto): si la app se abre en `http://localhost:5173` mientras `VITE_API_URL` apunta a la IP LAN (`192.168.1.81:8000`), el navegador trata ambos como **sitios distintos** (el host literal difiere, el puerto no es lo que importa) y bloquea la cookie `SameSite=Strict` — el refresh token quedaba inservible exactamente para quien abre la app desde el acceso directo de escritorio del PC servidor. Confirmado el diagnóstico abriendo por la IP LAN en vez de `localhost`: ahí sí funciona todo el ciclo (cookie seteada, renovación silenciosa, logout).

Corregido en `start.bat`: ahora lee el host de `VITE_API_URL` (`frontend\.env`) y abre el navegador con ese mismo host en vez de `localhost` a secas (con fallback a `localhost` si no encuentra el archivo).

**4. Verificación end-to-end**

- `pytest`: 6/6 en verde.
- Backend real (puerto 8000, bind `0.0.0.0`) + frontend real (puerto 5173, bind `0.0.0.0`) levantados a mano; flujo completo probado con `curl` (login → refresh con rotación → reuso del token viejo da `401` → logout → refresh después de logout da `401`) y con Playwright en Chromium real (login → cookie `HttpOnly` confirmada → access token inválido + reload → renovación silenciosa sin perder la sesión → logout → vuelve al login). Ambos servidores de prueba y Playwright se detuvieron/desinstalaron al terminar.

### Commits de esta sesión

```
9aa4193  feat(seguridad): refresh tokens con rotacion + bajar TTL de access token a 1h
6fbbd2c  fix(start): abrir el navegador con el mismo host que VITE_API_URL
```

### Pendientes / riesgos conocidos restantes (del listado del 18 de junio)

3. ~~Sin backups automatizados de PostgreSQL.~~ → resuelto el 19 de junio para SQLite, ver sesión de backups más abajo.
4. ~~Sin TLS — aceptable temporalmente por ser LAN cerrada.~~ → resuelto el 19 de junio con HTTPS + CA local, ver sesión más abajo (de paso la cookie del refresh token ya quedó con `Secure=True`). Queda pendiente instalar la CA en los 4 PCs cliente.
5. ~~`rol` sin constraint en BD.~~ → resuelto el 19 de junio, ver sesión más abajo. IDs secuenciales (no UUID) sigue sin tocar.
6. ~~Reset de contraseña por Admin — sugerido, no implementado.~~ → resuelto el 19 de junio, ver sesión más abajo.
7. Logo en mejor resolución si aparece el archivo original.

---

## Sesión — 19 de junio 2026 (continuación) — Backups automatizados

### Resumen

Se implementó el respaldo automatizado de la base de datos — resuelve el pendiente #3 anotado al cierre de la sesión del 18 de junio. Antes de implementar se aclaró una discrepancia real: el README pedía backups de **PostgreSQL**, pero la base que corre en producción (este PC servidor) es **SQLite** — PostgreSQL solo existe en el `docker-compose.yml`, que no se usa. Se acordó con el usuario el alcance: solo SQLite, destino otra carpeta en el mismo disco (`C:\SuperOzono-Backups`, no hay otro disco físico en este PC), con cifrado.

### Lo que se hizo

**1. Scripts de backup y restore**

- `backend/scripts/backup_db.py`: copia consistente de la BD en uso vía la API de backup de `sqlite3` (no corrompe aunque el backend esté escribiendo en ese momento), la cifra con `Fernet` (librería `cryptography`, ya estaba instalada como dependencia transitiva de `python-jose[cryptography]` — se declaró explícita en `requirements.txt` ya que ahora el backup depende directamente de ella), y borra backups con más de `BACKUP_RETENTION_DAYS` (30) días.
- `backend/scripts/restore_db.py`: descifra un backup y lo restaura sobre `backend/superozono.db`, guardando antes una copia `.bak-<fecha>` de la base actual por seguridad.
- Nuevas variables en `config.py` + `.env` (real, con clave generada) + `.env.servidor` (plantilla, con instrucciones para generar una clave propia por PC): `BACKUP_DIR`, `BACKUP_ENCRYPTION_KEY`, `BACKUP_RETENTION_DAYS`.

**2. Tarea programada en Windows**

`SuperOzonoERP-BackupDB` en el Programador de tareas de Windows, diaria a las 2:00am, corre `venv\Scripts\python.exe scripts\backup_db.py`. Creada y disparada manualmente una vez para confirmar que funciona fuera de una ejecución interactiva (`LastTaskResult: 0`, generó su backup correctamente).

**3. Verificación end-to-end**

- Backup manual → comparación de hashes crudos del archivo original vs. el restaurado: **no coinciden** (esperado — la API de backup de SQLite reorganiza páginas internamente, no produce un archivo byte-idéntico) pero el **contenido lógico sí es idéntico** (`conn.iterdump()` produce el mismo SQL en ambos, mismo largo). `PRAGMA integrity_check` → `ok`.
- `restore_db.py` corrido de verdad contra la BD real: creó la copia `.bak` y restauró correctamente (el backend sigue funcionando después, `usuarios` con el mismo conteo).
- `pytest`: 6/6 en verde. `flake8` limpio en los archivos nuevos.

### Commit de esta sesión

```
9d98001  feat(backups): respaldo diario cifrado de la BD SQLite
```

### Pendientes / riesgos conocidos restantes (del listado del 18 de junio)

4. ~~Sin TLS — aceptable temporalmente por ser LAN cerrada.~~ → resuelto el 19 de junio con HTTPS + CA local, ver sesión más abajo. Queda pendiente instalar la CA en los 4 PCs cliente.
5. ~~`rol` sin constraint en BD.~~ → resuelto el 19 de junio, ver sesión más abajo. IDs secuenciales (no UUID) sigue sin tocar.
6. ~~Reset de contraseña por Admin — sugerido, no implementado.~~ → resuelto el 19 de junio, ver sesión más abajo.
7. Logo en mejor resolución si aparece el archivo original.

### Riesgo nuevo anotado

8. Backups guardados en el mismo PC que la BD real (`C:\SuperOzono-Backups`) — no protege ante una falla total del PC (disco, robo, incendio). Tampoco la clave de cifrado (`BACKUP_ENCRYPTION_KEY`), que hoy vive solo en `backend/.env` de esta máquina. Pendiente: copiar periódicamente backups + clave a un destino fuera de este PC (red local, NAS o nube) cuando el usuario decida cuál.

---

## Sesión — 19 de junio 2026 (continuación) — HTTPS

### Resumen

Se implementó HTTPS para el ERP — resuelve el pendiente #4 anotado al cierre de la sesión del 18 de junio. Antes de implementar se aclaró otra discrepancia real (la tercera del día, después de Redis y Postgres): el pendiente del README apuntaba a `nginx.conf` y sugería Let's Encrypt, pero **el nginx es del stack Docker que no se usa**, y Let's Encrypt no es viable sin un dominio público — acá solo hay una IP LAN. Se acordó con el usuario avanzar igual con un certificado autofirmado, asumiendo el trabajo manual de instalarlo en los 4 PCs cliente.

### Lo que se hizo

**1. CA local + certificado de servidor**

`backend/scripts/generate_tls_cert.py` (librería `cryptography`, ya estaba instalada): genera una CA local autofirmada (`certs/superozono-ca.crt` + `.key`, válida 10 años) y, firmado por ella, un certificado de servidor (`certs/server.crt` + `.key`, válido ~2 años) con SAN de tipo IP para la IP LAN (detectada automáticamente leyendo `frontend/.env`) más `localhost`/`127.0.0.1`. La ventaja de separar CA y certificado de servidor: el certificado se puede regenerar (otra IP, vencimiento) sin tener que reinstalar nada en los 4 PCs cliente, mientras la CA no cambie. Todo `certs/` quedó en `.gitignore` — la clave privada de la CA nunca debe llegar a git.

**2. `start.bat` y Vite con TLS real**

- `start.bat`: si no existe `certs\server.crt` lo genera la primera vez; arranca `uvicorn` con `--ssl-keyfile`/`--ssl-certfile`; abre el navegador y muestra los mensajes finales con `https://`.
- `frontend/vite.config.ts`: si `certs/server.key` y `.crt` existen, configura `server.https` automáticamente — no hace falta pasarle flags a Vite.
- `CORS_ORIGINS` y `VITE_API_URL` pasados a `https://` en los `.env` reales y en las plantillas `.env.servidor`.
- Cookie del refresh token: `secure=True` en `_set_refresh_cookie` (`usuarios/router.py`) — ya no queda viajando en claro.

**3. Bug encontrado en los tests por el cambio anterior**

Al poner `secure=True`, `test_refresh_token_rotation` y `test_logout_revoca_refresh_token` empezaron a fallar: el cookie jar de `httpx` no reenvía cookies `Secure` sobre un `base_url` con esquema `http`. Se cambió el `base_url` del cliente de test a `https://testserver` en `conftest.py` — `ASGITransport` no abre sockets reales, así que no hace falta TLS de verdad para que el cookie jar se comporte bien.

**4. Verificación end-to-end (la más completa de las sesiones de hoy)**

- CA instalada como confiable en el almacén del usuario actual de este PC (`certutil -user -addstore -f "ROOT" certs\superozono-ca.crt`, sin necesitar permisos de administrador).
- `start.bat` corrido de verdad (no solo los comandos sueltos por separado) vía `Start-Process`: confirmado que ambos puertos quedan escuchando con TLS real, que el `--ssl-keyfile`/`--ssl-certfile` con rutas que tienen espacios (`...\MI PC\...`) se parsea bien a pesar del anidado de comillas, y que el navegador se abre solo en la URL `https://` correcta.
- `curl` con `--ssl-no-revoke` (en Windows, `curl` usa `schannel`, que por defecto exige info de revocación que una CA interna offline no tiene — falla con `CRYPT_E_NO_REVOCATION_CHECK` sin ese flag; no es un problema real, los navegadores no son tan estrictos).
- Playwright en Chromium real: la página principal carga con `200` (la CA fue aceptada sin errores de certificado), login funciona sobre HTTPS, y la cookie del refresh token sale con `{httpOnly: true, secure: true, sameSite: 'Strict'}`.
- `pytest`: 6/6 en verde. `flake8`/`eslint` limpios en los archivos nuevos.
- Procesos y ventanas de la prueba real de `start.bat` (incluyendo el Chrome que se abrió solo) detenidos al terminar.

### Commits de esta sesión

```
9df94b1  feat(seguridad): HTTPS con CA local autofirmada (uvicorn + Vite)
```

### Pendiente real para el usuario (no lo puede hacer el asistente)

Instalar `certs\superozono-ca.crt` como certificado raíz de confianza en los otros 4 PCs (instrucciones paso a paso en `DOCUMENTACION.md`, sección 6). Sin ese paso, esos 4 PCs van a ver "conexión no segura" al entrar al ERP — sigue funcionando, pero con la advertencia del navegador.

### Pendientes / riesgos conocidos restantes (del listado del 18 de junio)

5. ~~`rol` sin constraint en BD.~~ → resuelto el 19 de junio, ver sesión más abajo. IDs secuenciales (no UUID) sigue sin tocar.
6. ~~Reset de contraseña por Admin — sugerido, no implementado.~~ → resuelto el 19 de junio, ver sesión más abajo.
7. Logo en mejor resolución si aparece el archivo original.
8. Backups guardados en el mismo PC que la BD real (ver sesión de backups arriba).

---

## Sesión — 19 de junio 2026 (continuación) — Reset de contraseña por Admin

### Resumen

Se implementó el reset de contraseña por Admin para usuarios sin acceso — resuelve el pendiente #6, que venía marcado como *"sugerido, no implementado, pendiente de aprobación"* desde la sesión del 18 de junio (nunca era una decisión tomada). Se confirmó el diseño con el usuario antes de tocar código: el Admin escribe directamente la contraseña nueva (no hay flujo de email/token porque el proyecto no tiene infraestructura de correo), sin forzar cambio en el próximo login.

### Lo que se hizo

**1. Backend**

`PUT /v1/usuarios/{id}/reset-password` (solo Admin, `SuperuserDep`, igual que el resto del CRUD de usuarios): valida mínimo 8 caracteres y reescribe `hashed_password` directamente, sin pedir la contraseña actual (a diferencia de `/usuarios/me/password`, que sí la pide). Esquema nuevo `UsuarioPasswordReset` en `schemas.py`.

**2. Frontend**

Botón "🔓 Resetear contraseña" junto a cada usuario en `UsuariosView.tsx` (al lado de Editar/Activar-Desactivar), abre un modal (`ResetPasswordModal`) donde el Admin tipea la contraseña nueva dos veces. Sin campo de "contraseña actual" — esa es justo la diferencia con el modal de "Cambiar mi contraseña" que ya existía.

**3. Bug real encontrado en el camino (no es del reset de contraseña — es de logout)**

Verificando el flujo completo en un navegador real (crear usuario → resetear contraseña → cerrar sesión → loguear como el usuario afectado), el clic en "Cerrar Sesión" a veces **no cerraba la sesión**: el usuario volvía a aparecer logueado solo. Causa: `logout()` limpiaba el estado local (`token`/`user`) *antes* de que el backend terminara de revocar el refresh token; eso disparaba en paralelo el efecto de "renovación silenciosa" (agregado en la sesión de refresh tokens, se activa cuando `token` pasa a `null`), y a veces el `POST /login/refresh-token` le ganaba la carrera al `POST /login/logout` — conseguía un access token nuevo antes de que el refresh token quedara invalidado en la BD, re-logueando solo a quien acababa de cerrar sesión. Confirmado con los logs del backend: se veía `refresh-token 200 OK` *después* de `logout 200 OK`.

Corregido haciendo que `logout()` espere (`await`) la respuesta de `/login/logout` antes de limpiar el estado local — así, cuando el efecto de renovación silenciosa se dispara, el refresh token ya está revocado en el servidor y el intento falla como corresponde (`401`).

**4. Verificación end-to-end**

- `pytest`: 8/8 en verde (2 tests nuevos: reset + login con la contraseña nueva confirmando que la vieja ya no funciona; un no-Admin recibe `403`).
- Navegador real (Playwright, instalado temporalmente): creado un usuario de prueba, reseteada su contraseña desde la UI, confirmado que el login con la contraseña vieja falla y con la nueva entra correctamente mostrando su rol (Auxiliar) y las vistas que le corresponden. Repetido después de arreglar el bug de logout para confirmar el ciclo completo (login → crear → resetear → **logout real** → login del afectado) de punta a punta.
- Usuarios de prueba y sus refresh tokens borrados de la BD real al terminar; Playwright desinstalado.

### Commits de esta sesión

```
824d6f4  fix(auth): race condition entre logout y renovacion silenciosa de sesion
54334c2  feat(usuarios): reset de contraseña por Admin para usuarios sin acceso
```

### Pendientes / riesgos conocidos restantes (del listado del 18 de junio)

5. ~~`rol` sin constraint en BD.~~ → resuelto el 19 de junio, ver sesión más abajo. IDs secuenciales (no UUID) sigue sin tocar.
7. Logo en mejor resolución si aparece el archivo original.
8. Backups guardados en el mismo PC que la BD real.
9. Instalar la CA local (`certs\superozono-ca.crt`) en los 4 PCs cliente (ver sesión de HTTPS arriba).

---

## Sesión — 19 de junio 2026 (continuación) — Constraint de rol en BD

### Resumen

Se agregó un `CHECK constraint` real sobre `usuarios.rol` — resuelve la mitad del pendiente #5 (la otra mitad, IDs secuenciales/UUID, queda igual, el usuario solo pidió el constraint de rol). En el camino, migrar la BD real rompió las foreign keys de otras 3 tablas — encontrado, reparado y corregido antes de seguir.

### Lo que se hizo

**1. CHECK constraint + fuente única de verdad**

`backend/app/modules/usuarios/models.py`: `ROLES_VALIDOS = ("Admin", "Administradora", "Auxiliar")` ahora vive ahí, con un `CheckConstraint` en `__table_args__` del modelo `Usuario`. `router.py` importa esa misma tupla en vez de tener su propia copia (`ROLES_VALIDOS = {...}` duplicado, riesgo real de que las dos listas se desincronizaran con el tiempo).

**2. Migración para la BD existente**

`backend/scripts/migrate_rol_constraint.py`: SQLite no soporta `ALTER TABLE ADD CONSTRAINT`, así que recrea la tabla `usuarios` (rename → create con el constraint → copiar datos → drop → recrear índices). Idempotente.

**3. Bug real encontrado al correr la migración sobre la BD real**

Al ejecutar el script la primera vez, `PRAGMA foreign_key_check` mostró que `refresh_tokens`, `movimientos_inventario` y `pagos` quedaron con sus `FOREIGN KEY` apuntando a `usuarios_old` en vez de `usuarios`. Causa: `ALTER TABLE ... RENAME TO` en SQLite moderno (≥3.25, default) reescribe automáticamente las foreign keys de **otras** tablas para que sigan el renombre — comportamiento pensado para renombrar una tabla de forma permanente, no para la técnica de "recrear para agregar un constraint" donde el nombre final vuelve a ser el mismo.

Reparación de la BD real (sin pérdida de datos, verificado con conteo de filas + `PRAGMA integrity_check` + `foreign_key_check` antes/después): backup de seguridad del `.db`, y luego `PRAGMA writable_schema=ON` para reescribir directamente el texto SQL guardado en `sqlite_master` de esas 3 tablas (de `"usuarios_old"` a `"usuarios"`), sin tocar ninguna fila de datos.

Corrección del script para que esto no se repita: `PRAGMA legacy_alter_table=ON` antes del rename (evita que SQLite reescriba las FKs de otras tablas) + una verificación automática post-migración (`foreign_key_check` + `integrity_check`) que aborta si algo quedó mal. Probado el fix en una base de datos aislada (con una tabla extra referenciando `usuarios` por FK, replicando el escenario real) antes de confiar en él.

**4. Test nuevo**

Inserta un usuario con `rol="Hacker"` directo por el ORM (bypaseando toda validación de la API) y confirma que la BD lo rechaza con `IntegrityError`. Requirió agregar un fixture `db_session` a `conftest.py` — intentar `from tests.conftest import TestingSessionLocal` directamente desde el archivo de test duplicaba el módulo (pytest ya lo carga por su cuenta), y el segundo `engine` apuntaba a una base SQLite en memoria distinta y vacía (`no such table: usuarios`).

**5. Verificación final**

`pytest`: 9/9 en verde. `flake8` limpio. BD real: `PRAGMA integrity_check` → `ok`, `foreign_key_check` → sin problemas, conteo de filas igual antes/después en las 4 tablas afectadas, y un login real funcionando contra la base ya migrada.

### Commit de esta sesión

```
1c3bbc0  feat(usuarios): CHECK constraint en rol + migracion para la BD existente
```

### Pendientes / riesgos conocidos restantes (del listado del 18 de junio)

7. Logo en mejor resolución si aparece el archivo original. *(Revisado el 19 de junio — el archivo que apareció era la misma captura de baja resolución de siempre, no uno nuevo. Sigue pendiente.)*
8. Backups guardados en el mismo PC que la BD real. *(Revisado el 19 de junio — se evaluó OneDrive, ya instalado pero sin cuenta conectada, y una carpeta compartida en otro PC/NAS de la red. Se dejó pendiente sin elegir destino todavía.)*
9. Instalar la CA local (`certs\superozono-ca.crt`) en los 4 PCs cliente.
10. IDs secuenciales (no UUID) — deuda técnica, no urgente en este contexto.

---

## Sesión — 19 de junio 2026 (continuación) — Verificación general + fix de bug real

### Resumen

A pedido del usuario, verificación integral de todo lo trabajado en el día: bugs, limpieza de código, estado de git, y qué quedó guardado local vs. en el repo. Encontrado y corregido un bug real preexistente (no relacionado a ninguna de las sesiones de hoy) en el módulo de Contabilidad.

### Lo que se hizo

**1. Verificación**

- `pytest` 9/9, `flake8`/`eslint`/`tsc` sin hallazgos nuevos en lo de hoy.
- `git fetch` + comparación: rama local idéntica a `origin/main`, sin commits pendientes de subir.
- Confirmado que lo que debe quedar solo local está (`backend/.env`, `certs/`, `backend/superozono.db`, `C:\SuperOzono-Backups`, la tarea programada) y que las plantillas correspondientes están versionadas en git sin secretos reales.
- Sin archivos de prueba o debug sueltos en el repo.

**2. Bug real encontrado: `EstadoPeriodo` no importado en `contabilidad/router.py`**

`create_periodo()` y `toggle_periodo()` usaban `EstadoPeriodo` (de `contabilidad/models.py`) sin importarlo — `NameError` en cada llamada, devolviendo `500` siempre. Afecta a `POST /api/v1/contabilidad/periodos` y `PATCH /api/v1/contabilidad/periodos/{id}/toggle`, ambos usados por `PeriodosView.tsx` en el frontend (crear período nuevo y abrir/cerrar uno existente estaban rotos en producción). Confirmado en vivo antes y después del fix (`500` → `201`/`200`).

Fix: agregar `EstadoPeriodo` al import existente. Una línea.

### Commit de esta sesión

```
cd7f708  fix(contabilidad): NameError al crear o togglear un periodo contable
```

---

## Sesión — 1 de julio 2026 — Mejoras de frontend + auditoría y fixes de backend

### Resumen

Sesión larga en dos frentes. **Frontend:** refactor de visualización (componentes compartidos, accesibilidad, responsive, skeletons) y exposición del perfil tributario del cliente. **Backend:** revisión profunda tipo "code review senior" de todos los módulos y BD, seguida de la implementación por fases de los hallazgos de mayor valor. Todo quedó **commiteado en local (rama `mejoras-frontend`), sin push** — a pedido del usuario, por ahora solo local. Suite de tests: de 113 → **123/123 en verde**; type-check y build del frontend limpios.

### Lo que se hizo

**1. Frontend — refactor de visualización**

- Se extrajeron `Toast` y `Modal` (duplicados inline en casi todas las vistas) a componentes compartidos y accesibles en `frontend/src/components/`: `Toast.tsx` (`role="status"`, `aria-live`) y `Modal.tsx` (focus-trap, cierre con `Escape`, `role="dialog"`+`aria-modal`, restauración de foco). Adoptados en las 10 vistas; se convirtieron también los modales de formulario (CentrosCosto, Nomina, Puc, Tributarios).
- **Skeleton loaders**: nuevo `Skeleton.tsx` + CSS shimmer, aplicado en Dashboard (elimina el salto de layout) y en las 5 vistas de lista de contabilidad.
- **Accesibilidad** (`index.css`): `:focus-visible` global y `@media (prefers-reduced-motion: reduce)`.
- **Responsive** (`index.css`): breakpoints 1024/768/480, sidebar más angosta, grids apilados, tablas con scroll horizontal, botones full-width en móvil. La sidebar ya tenía toggle de colapso manual.
- **Estilos inline → utilidades**: `.form-vertical`, `.form-grid-2`, `.form-actions`, `.row-actions`, `.section-label` (25 reemplazos).
- Fix de bug preexistente `TS2488` (`.filter(Boolean)` no estrecha `null`) en `printFactura.ts`, `printCompra.ts` y `ComprasView.tsx` (2 sitios). Bloqueaba el build.

**2. Backend — revisión profunda (bloque 1: correctitud/robustez)**

- **Validación de entradas** en schemas (ventas/compras/contabilidad): `gt=0` en abonos y valores de CxC/CxP, `gt=0` cantidad, `ge=0` precios, `0–100` en descuentos e IVA. Bloquea abonos negativos, precios negativos y % fuera de rango.
- **Guard de sobreventa** en `confirmar_venta`: valida stock disponible y devuelve `400` antes de descontar (antes dejaba stock negativo en silencio).
- **N+1 eliminado** en `list_ventas`/`get_venta` con `selectinload` + helper `_build_venta_response` (601 → ~3 queries con 100 ventas).
- **Numeración robusta unificada** en nuevo `core/numbering.py` (`MAX` del sufijo + parseo tolerante), reemplaza el `COUNT+1`/`max+1` frágil en ventas, compras y comprobantes RC/CE.
- **Dashboard**: "ventas por marca" ahora excluye ventas ANULADAS (en el `ON` del LEFT JOIN, sin perder productos sin ventas).

**3. Backend — bloque 2 (features / decisiones)**

- **Admin del seed por env var** (`SEED_ADMIN_EMAIL`/`SEED_ADMIN_PASSWORD` en `config.py`), con warning si sigue la contraseña de fábrica.
- **Auto-CxC al confirmar venta** (espejo de compras→CxP), vinculada por `numero_factura`, idempotente.
- **Stock fraccionario**: `Producto.stock_actual` y los snapshots del kardex (`stock_antes/despues`) migrados a `Numeric(12,3)`; el servicio ya no redondea (`int(round)` eliminado); `field_serializer` mantiene el stock como número en la API para no romper el frontend.
- **Retenciones en ventas — modelo híbrido** (era hardcodeado 2.5%/15%): perfil tributario del cliente (flags nuevos `retiene_fuente/iva/ica`, `tarifa_reteica`) + tarifas desde `ParametroTributario` + tope en UVT configurable (`UVT_VALOR`, `RETEFUENTE_BASE_UVT`) + **override manual por factura**. `reteica` ya se calcula (antes siempre 0). Helper `_sugerir_retenciones`.
- **Migración SQLite** `scripts/migrate_cliente_retenciones.py` (idempotente, `ADD COLUMN`) para las columnas nuevas de `clientes` en la BD real. **Ya ejecutada** contra `superozono.db`.

**4. Frontend — flags de retención**

Formulario de Cliente (`VentasView.tsx`) ahora tiene la sección "Perfil tributario" con checkboxes ReteFuente/ReteIVA/ReteICA y el campo Tarifa ReteICA (por mil). Tipo `Cliente` actualizado en `ventasApi.ts`.

**5. Tests**

Nuevo `tests/test_validaciones.py` (10 casos: abono ≤0, venta inválida, sobreventa 400, stock fraccionario, numeración secuencial, auto-CxC, retenciones por perfil, override manual). Se actualizaron 2 tests que codificaban la lógica vieja de retenciones (`test_unitarias`, `test_bugs` BUG-010b) y `conftest.py` siembra las tarifas de retención. **123/123 en verde.**

### Commits de esta sesión (LOCAL — sin push)

```
944898d  feat(frontend): componentes compartidos, accesibilidad, responsive y flags de retención
6cafaba  fix(backend): validaciones, integridad de inventario y motor de retenciones
```

### Cómo correr en local (notas de entorno)

- El `venv` del backend está **roto** (creado en otra máquina, usuario "MI PC"). Esta sesión se corrió con el Python del sistema (`C:\Program Files\Python313`), donde se instaló `uvicorn`. **Pendiente recrear el venv** (`python -m venv venv` + `pip install -r requirements.txt`).
- Local: backend `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --ssl-keyfile ../certs/server.key --ssl-certfile ../certs/server.crt`; frontend `npm run dev -- --host 0.0.0.0` (queda en `https://localhost:5173`).
- Se creó `frontend/.env.local` (ignorado por git) apuntando `VITE_API_URL=https://localhost:8000/api` para desarrollo en esta máquina.
- Recordatorio: hay que **aceptar el certificado autofirmado del backend** (`https://localhost:8000`) en el navegador, si no el frontend no puede llamar a la API.

### Pendientes / lo que falta (para la próxima sesión)

**Recomendado antes de producción (backend, aplica en local):**
1. Refresh tokens: el `delete` del token de usuario inactivo se revierte por el rollback del `raise`; los tokens expirados nunca se limpian (tabla crece).
2. `int(token_data.sub)` en `deps.py` puede dar 500 en vez de 401.
3. Auto-lockout de Admin: puede cambiarse el rol a sí mismo / dejar el sistema sin admins (falta guard de "último admin").
4. Enumeración de usuarios: el login da mensajes distintos ("Usuario inactivo" vs credenciales).
5. Paginación en listados (`list_ventas`, `list_compras`, `productos`) — hoy cargan todo.

**Opcionales / calidad:**
6. Unificar `estado` Enum vs String (ventas usa `SAEnum`, compras usa string).
7. `EmailStr` en cliente/proveedor (diferido por acoplamiento Base/Response).
8. `_enrich_cxc/cxp` usan `{**__dict__}` (frágil).
9. Alegra: POST donde debería PUT para actualizar (BUG-007 del REPORTE_BUGS.md).
10. Frontend menor: form de producto usa `parseInt` para stock inicial (no fraccionario); lista/detalle de cliente no muestra los flags de retención (solo el formulario).

**Solo al desplegar al servidor / PostgreSQL (no aplica en local):**
11. **Alembic** (migraciones) — para aplicar en Postgres los cambios de columnas/tipos hechos en SQLite (stock a Numeric, columnas de retención en clientes).
12. Locks de concurrencia (`with_for_update`) en abonos y stock — evita lost-update/sobrepago en multi-worker.
13. `datetime` tz-aware — quitar el deprecation de `utcnow()` (delicado por la comparación del refresh token; requiere `DateTime(timezone=True)`).

**Config / negocio (no es código):**
14. Confirmar `UVT_VALOR` con el contador (hoy placeholder = 49799, UVT 2025) y **activar los flags `retiene_*`** en los clientes que sean agentes retenedores.

**Nota:** esta sesión NO se pusheó a GitHub. Cuando se decida subir, revisar que `.env.local`, `venv/` y `superozono.db` sigan ignorados (lo están).

---

## Sesión — 2 de julio 2026 — Overhaul de calidad, seguridad y cobertura (Claude Fable 5)

### Resumen

La sesión más grande del proyecto hasta la fecha: **10 commits en local** (sin push, a pedido del usuario). Tres frentes: (1) calidad de código — tipado SQLAlchemy 2.0 completo, mypy en cero, tooling de QA formalizado, CI en GitHub Actions, Alembic; (2) **seguridad** — 14 CVEs eliminados y todos los hallazgos accionables del `REPORTE_SEGURIDAD.md` resueltos; (3) **cobertura de tests: 123 → 178 tests, cobertura real 95%** (se descubrió que coverage medía mal el código async). Frontend: code splitting (bundle inicial −39%), ErrorBoundary y primeros tests con Vitest.

### Lo que se hizo

**1. Infraestructura de calidad**

- `venv` del backend recreado (estaba roto, apuntaba al PC anterior "MI PC") — resuelve el pendiente de la sesión del 1 de julio.
- `requirements-dev.txt` nuevo con pytest/flake8/mypy/pre-commit/pip-audit pineados (antes no estaban declarados en ningún lado).
- Configs formales: `backend/.flake8` (línea 120), `backend/mypy.ini`, `backend/.coveragerc`, `pytest.ini` sin `--disable-warnings`.
- **Migración de modelos a SQLAlchemy 2.0 tipado** (`Mapped`/`mapped_column`) en ventas, compras, inventario y contabilidad → **mypy: 161 errores → 0**.
- `datetime.utcnow()` (deprecado) reemplazado por helper `utcnow()` naive-UTC en `core/time.py` — resuelve el pendiente #13 del 1 de julio. Warnings de pytest: 1189 → 1.
- Pydantic modernizado: `class Config` → `model_config` / `SettingsConfigDict`.
- **Alembic async** configurado (`backend/alembic/`, URL desde el `.env` de la app, batch mode para SQLite) con **migración baseline** verificada con `alembic check`; la BD de dev quedó `stamp head` — resuelve el pendiente #11.
- **CI en GitHub Actions** (`.github/workflows/ci.yml`): flake8 + mypy + pytest con cobertura (backend), ESLint + tsc + Vitest + build (frontend), pip-audit (seguridad). Dependabot semanal para pip/npm/actions.
- Line endings normalizados en todo el repo (`.gitattributes` + `.editorconfig` + `git add --renormalize`).
- **pre-commit** configurado e instalado (checks básicos + flake8) — ya validó los commits reales de la sesión.

**2. Seguridad (ver actualización en `REPORTE_SEGURIDAD.md`)**

- **14 CVEs → 0**: `python-multipart` 0.0.20→0.0.31, `fastapi` 0.115→0.139, `starlette` 0.46.2→1.3.1.
- SEC-001/007: `/docs`, `/redoc`, `/openapi.json` y datos del sistema en `/` solo con `DEBUG=true`.
- SEC-004: access token de 1h → **15 min** (`ACCESS_TOKEN_EXPIRE_MINUTES`, renombrada en código, `.env` local y las 3 plantillas). **Al desplegar al servidor: renombrar la variable en su `.env`.**
- SEC-005: rate limiting en `reset-password` (5/min) y `me/password` (10/min).
- SEC-006: `Settings` rechaza `CORS_ORIGINS=*` con `DEBUG=false` (la app no arranca).
- SEC-009: sync de Alegra usa `PUT` para actualizar contactos/items (el POST podía duplicar) — resuelve el pendiente #9.
- Headers de seguridad en todas las respuestas (middleware ASGI puro): `nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy`, HSTS.

**3. Cobertura de tests (123 → 178, cobertura real 95%)**

- **Hallazgo clave:** pytest-cov no trazaba el código dentro de los greenlets de SQLAlchemy async — la cobertura reportada (70%) era falsa. Con `concurrency = greenlet` en `.coveragerc`, la real era 82%; se subió a **95%**.
- Tests nuevos: flujo de ventas (13), gestión de usuarios (8), maestros contables (7), cartera CxC/CxP con comprobantes RC-/CE- (8), flujo de compras con CxP e inventario (8), integración Alegra con HTTP mockeado (11), seguridad SEC (4+).
- Módulos al final: compras/router **100%**, ventas/router 97%, usuarios/router 97%, contabilidad/router 95%, alegra/router 94%.

**4. Frontend**

- `useAuth` separado a `contexts/auth.ts` (arregla el error de ESLint react-refresh; ESLint queda en 0).
- **Code splitting** con `React.lazy` por vista: bundle inicial 426 kB → **259 kB**.
- **ErrorBoundary** en la zona de contenido (fallback recuperable con "Reintentar").
- **Vitest + Testing Library** configurados, 5 tests iniciales (`useAuth`, `ErrorBoundary`), scripts `npm run test`/`test:watch`, integrado al CI.

### Commits de esta sesión (LOCAL — sin push, 10 en total)

```
569e626  feat(frontend): code splitting, ErrorBoundary y suite de tests con Vitest
294000c  refactor(backend): SQLAlchemy 2.0 tipado, mypy limpio y tooling de QA
4881e85  feat(backend): migraciones Alembic async con baseline del esquema completo
43fa981  ci: GitHub Actions, Dependabot, cobertura y documentacion de QA
7a1a7cc  chore: normalizar finales de linea en todo el repo
af7336b  test(backend): flujo completo de ventas y gestion de usuarios + cobertura real
418c9d2  chore: hooks de pre-commit y documentacion de QA actualizada
64d82e8  security: resolver hallazgos del reporte de seguridad + 14 CVEs de dependencias
85a3cb5  test(backend): cartera, compras y maestros contables — cobertura 82% -> 91%
9858d99  test(backend): integracion Alegra con cliente HTTP mockeado
```

### Estado de los pendientes de la sesión del 1 de julio

- ✅ Resueltos hoy: venv recreado, #9 (Alegra PUT), #11 (Alembic), #13 (utcnow tz).
- ⏳ **Siguen abiertos** (backend, robustez de auth): #1 limpieza de refresh tokens expirados, #2 `int(token_data.sub)` puede dar 500, #3 guard de "último admin", #4 enumeración de usuarios en login, #5 paginación de listados. También #6-8, #10 (calidad menor), #12 (locks de concurrencia, solo multi-worker) y #14 (confirmar UVT con el contador).

### Pendientes para próximas sesiones

1. Tests de frontend para vistas críticas (Login, Cartera/Ventas) — en curso.
2. **Motor de asientos contables (partida doble)** → P&L y Balance General. Requiere validar el mapeo PUC con el contador.
3. Push a GitHub (dispara el CI por primera vez).
4. Backups fuera del PC servidor (riesgo #1 operacional).
5. Al desplegar: `pip install -r requirements.txt`, renombrar `ACCESS_TOKEN_EXPIRE_*` en el `.env` del servidor, `alembic stamp head` una vez.
