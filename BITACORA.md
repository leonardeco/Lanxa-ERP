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

---

## Sesión — 2 de julio 2026 (continuación) — Motor contable, estados financieros, E2E y entrega funcional

### Resumen

Continuación de la sesión del overhaul: se construyó el **motor de asientos contables (partida doble)** y sobre él los **estados financieros (P&L y Balance General)** con UI completa y export a Excel; se cerraron los 5 pendientes de robustez de auth del 1 de julio; se agregó la tercera capa de tests (**E2E con Playwright**); se hizo el **primer push a GitHub** (CI en verde al primer intento) y se procesó la primera tanda de Dependabot. Al cierre: **198 tests de API + 25 de componentes + 5 E2E**, todo verde, local = remoto.

### Lo que se hizo

**1. Motor de asientos contables (partida doble automática)** — `backend/app/modules/contabilidad/asientos.py`

- Asiento automático al **confirmar venta** (DB 130505 Clientes + retenciones sufridas / CR 413595 Ingresos + 240801 IVA), al **confirmar compra** (DB 143501 Inventario + 240802 IVA descontable / CR 220501 Proveedores + retenciones practicadas) y al **abonar CxC/CxP** (Caja ↔ Clientes/Proveedores).
- **Reverso espejo al anular** — ambos asientos quedan activos y netean a cero (traza de auditoría); flag `reversado` evita reversos dobles.
- Valida el balanceo (rechaza asientos descuadrados), crea las cuentas PUC del mapeo si faltan y asigna período contable por fecha.
- **Materializa el registro único de terceros**: cada cliente/proveedor queda vinculado por NIT en los movimientos (`tercero_id`); un NIT que compra y vende pasa a tipo **Mixto**. Base lista para el auxiliar por tercero.
- Columnas nuevas `documento_ref` + `reversado` vía **migración Alembic** (`72f7b9fae762`) — el drift de nulabilidad legacy se dejó fuera a propósito (documentado en la migración).
- ⚠️ **Mapeo PUC en borrador**: ver `MAPEO-PUC-PARA-CONTADOR.md` (preguntas concretas para la contadora + pendiente de costo de venta 6135/1435).

**2. Estados financieros (API + UI)**

- `GET /reportes/estado-resultados` (P&L por período) y `GET /reportes/balance-general` (con saldos iniciales, resultado del ejercicio cerrando contra patrimonio y flag `cuadrado`).
- **3 pestañas nuevas en Reportes**: Estado de Resultados, Balance General (indicador "✓ Cuadrado") y **Libro Diario** (asientos expandibles, filtros por módulo/documento, badge de reversados).
- **Export a Excel en los 6 reportes** (`utils/exportCsv.ts`: BOM UTF-8, separador `;`, coma decimal — abre directo en Excel es-CO).
- **Panel de alertas de cartera en el Dashboard**: documentos vencidos y por vencer en 7 días (CxC y CxP).

**3. Robustez de auth (cerrados los pendientes #1-5 del 1 de julio)**

- Refresh tokens vencidos se purgan en cada login; el delete del token de usuario inactivo se commitea antes del raise (el rollback lo revertía).
- JWT con `sub` no numérico → 401 (antes 500). Guard de **último admin** (update y toggle). Mensaje único de login (anti-enumeración). Paginación `limit/offset` en los 6 listados grandes.

**4. Ops y entrega funcional**

- Fix real en `start.bat`/`stop.bat`: `> /dev/null` (sintaxis Unix) → `> nul` (6 ocurrencias).
- `DESPLIEGUE.md`: checklist de actualización del servidor con rollback.
- **Simulacro de recuperación ejecutado**: backup cifrado → BD destruida → restore → contenido idéntico (138 filas / 23 tablas). El procedimiento está probado, no solo escrito.
- `MANUAL-DE-USUARIO.md`: guía no técnica por flujos para los 4 usuarios.
- Búsqueda por texto en el catálogo de productos (clientes y proveedores ya la tenían).

**5. Tercera capa de tests: E2E con Playwright**

- `npm run test:e2e` levanta backend (puerto 8100, BD e2e sembrada) + frontend (5273, sin TLS vía flag `E2E=1` en `vite.config.ts`) y corre 5 flujos en Chromium: login inválido/válido, menú por rol, Ventas con búsqueda, reportes financieros (Balance "✓ Cuadrado") y logout.
- Los primeros runs atraparon 2 defectos reales de selectores (strict mode + pestaña inicial de Ventas) — corregidos.

**6. GitHub: push, CI y Dependabot**

- **Primer push** (16 commits) → CI verde al primer intento (backend 3m18s, frontend 53s, pip-audit 28s).
- Dependabot abrió 8 PRs a los segundos. Fusionados con CI verde: 3 de GitHub Actions (checkout v7, setup-python v6, setup-node v6), pip-menores (10 minors: SQLAlchemy 2.0.51, pydantic 2.13.4, uvicorn 0.49…), structlog 26.1, @types/node 26 y npm-menores (7).
- **Rechazado bcrypt 4.0.1→5.0**: su CI falló — passlib 1.7.4 (sin mantenimiento) no carga el backend de bcrypt ≥ 4.1. Comentado en el PR con `@dependabot ignore this major version`. **Pendiente técnico nuevo**: migrar `security.py` de passlib a bcrypt directo para desbloquear la actualización.
- Tras cada merge se re-validó el entorno local completo (198 + 25 + 5 tests).

### Commits de esta parte (pusheados a GitHub)

```
dae561c  feat(reportes)+fix(auth): P&L y Balance General + robustez de autenticacion
baaf165  feat(frontend): UI de estados financieros, libro diario y alertas de vencimiento
4dd4284  feat: exports a Excel, terceros en asientos, busqueda de productos y ops
39a013e  test(e2e): smoke con Playwright + manual de usuario final
+ 945612f (motor de asientos), ac56881 (bitácora), 2bb9653 (tests frontend) y 7 merges de Dependabot
```

### Pendientes

1. **Contadora**: validar `MAPEO-PUC-PARA-CONTADOR.md`, entregar PUC definitivo, inventario inicial y saldos de apertura (`SaldoInicial` está listo para recibirlos).
2. **Costo de venta** (asiento 6135/1435) — requiere definir método de costeo (promedio ponderado con el kardex actual es lo natural).
3. Migrar `security.py` de passlib a bcrypt directo (desbloquea bcrypt 5; probar login con hashes existentes).
4. Backups fuera del PC servidor (riesgo operativo #1).
5. Funcional de fases: devoluciones (notas crédito/débito), cotizaciones, RRHH/nómina, Electron, audit log.
6. Al desplegar al servidor: seguir `DESPLIEGUE.md` (incluye rename de `ACCESS_TOKEN_EXPIRE_*` y `alembic stamp`).

---

## Sesión — 3 de julio 2026 — Sprints 1-3 y Devoluciones (Claude Fable 5)

### Resumen

Ejecución del backlog en 4 bloques, cada uno commiteado, pusheado y con CI verde: **Sprint 1** (cartera a prueba de errores: anulación de abonos, cierre real de períodos, hora local Colombia), **Sprint 2** (auxiliar por tercero + logs persistentes), **Sprint 3** (passlib→bcrypt 5, DV del NIT, deuda de UI) y el feature **Devoluciones** (nota crédito full-stack + devolución a proveedor por API). Tests: 210 → **215 API + 25 componentes + 5 E2E**.

### Lo que se hizo

**Sprint 1 (`d29cb93`)** — 15a: `POST /cartera/pagos/{id}/anular` restaura saldo/estado de CxC/CxP, re-sincroniza la compra y reversa el asiento; comprobante queda `[ANULADO]` visible; botón ⛔ en el historial de pagos; migración `8a1c2f0d4b21`. 15b: `validar_periodo_abierto()` en el punto único del motor — período CERRADO bloquea confirmar/anular/abonar con rollback completo. 15c: `bogota_now()` para fechas de negocio (Pago, kardex); `tzdata` pineado (Windows no trae la base IANA).

**Sprint 2 (`9b18f80`)** — 15d: `GET /terceros/{id}/auxiliar` (estado de cuenta con saldo corrido, filtros por fecha/cuenta; cuadra contra la CxC por test) + pestaña "Auxiliar por Tercero" en Reportes con export. 14b: `core/logging_config.py` — RotatingFileHandler 5MB×5 en `backend/logs/` + structlog enrutado por stdlib (los errores de uvicorn también quedan en archivo).

**Sprint 3 (`a0d90b5`)** — 9: `security.py` migrado de passlib (sin mantenimiento) a bcrypt directo, **bcrypt 5.0.0**; compat con hashes existentes blindada por test con hash real pre-migración; truncado explícito a 72 bytes. 14e: `core/nit.py` con el algoritmo DIAN del dígito de verificación, validado en cliente/proveedor (verificado con el NIT real de la empresa: 901841798-5). 13c/13d: stock fraccionario en el form de producto y badges de retenciones en la lista de clientes.

**Devoluciones (`7e99aca`)** — NC-#### ventas full-stack: devolución parcial con tope acumulado por línea, reingreso a inventario, CxC reducida, asiento con cuenta nueva **417501 Devoluciones en ventas** (contra-ingreso: el P&L resta las NC automáticamente — test) y modal ↩️ en Facturas. ND-#### compras por API: valida stock (lo ya vendido no se puede devolver), reduce CxP, asiento espejo, balance sigue cuadrado (test). Migración `c3e9a17f5d02` (4 tablas). Limitación documentada: retenciones de la factura original no se ajustan en la NC.

### Incidencia de herramientas

Los heredocs de bash colapsan `\n` literales — corrompieron un string de Python 2 veces. Solución adoptada: bloques con caracteres especiales se escriben vía tool Write a scratchpad y se concatenan.

### Commits (todos con CI verde)

```
d29cb93  feat(cartera): Sprint 1 — anulacion de abonos, cierre de periodos real y hora local
a7f7b4a  docs: marcar Sprint 1 completado
9b18f80  feat(contabilidad): Sprint 2 — auxiliar por tercero y logs persistentes
3067278  docs: marcar Sprint 2 completado
a0d90b5  feat: Sprint 3 — bcrypt directo, validacion DV del NIT y deuda rapida de UI
7e99aca  feat: devoluciones — nota credito (ventas) y devolucion a proveedor (compras)
```

### Pendientes tras esta sesión

Ver `PENDIENTES.md` (7ª revisión). Próximos de código: botón de devolución en ComprasView (15-ui), cotizaciones (#16), audit log (#19). Bloqueados por la contadora: mapeo PUC, costeo (→ costo de venta #8), datos maestros.

---

## Sesión — 5 de julio 2026 — Cotizaciones (Claude Fable 5)

### Resumen

Feature **Cotizaciones (#16)** full-stack en un solo bloque: documento COT-#### con flujo comercial completo (Borrador → Enviada → Aprobada/Rechazada → Convertida), vigencia en días, conversión a venta reusando el flujo existente, PDF imprimible y pestaña nueva en el módulo de Ventas. Tests: 215 → **221 API + 25 componentes**.

### Lo que se hizo

**Backend (`3900182`)** — Modelos `Cotizacion`/`CotizacionDetalle` (mismas columnas de montos que ventas; `fecha_vencimiento = fecha + vigencia_dias`, default 15). Endpoints bajo `/api/v1/ventas/cotizaciones` (declarados antes de `/{venta_id}` para que la ruta literal no la capture el path param): listado con filtro por estado, detalle, creación (reusa `_calcular_detalle` y `next_sequential_numero`), y transiciones `enviar`/`aprobar`/`rechazar`/`convertir`. Reglas: aprobar valida que no esté vencida; rechazar acepta motivo opcional; convertir solo desde Aprobada y llama a `create_venta` directamente — la venta nace en **Borrador** con observación "Generada desde cotización COT-XXXX", sin efectos de inventario/contabilidad hasta confirmarla (verificado por test). La respuesta expone `vencida` (calculada) y `venta_numero`. Migración `d7a3c45e1b90` (2 tablas). 6 tests nuevos en `test_cotizaciones.py`.

**Frontend (mismo commit)** — Pestaña "📋 Cotizaciones" en Ventas: tabla con vencimiento resaltado si está vencida, badge por estado (Convertida en morado), acciones contextuales (📤 enviar, ✅ aprobar, ❌ rechazar con motivo, 🔁 convertir con confirmación), modal de detalle y `printCotizacion.ts` (PDF con caja de vigencia y nota "no constituye factura"). Modal Nueva Cotización con las mismas líneas de detalle que Nueva Venta + campo vigencia.

**Detalle técnico** — al convertir, la relación `cotizacion.venta` ya estaba cargada como `None` en el identity map y el `selectinload` del re-fetch no la refresca; se resolvió con `db.refresh(cot, attribute_names=["venta"])`.

### Pendientes tras esta sesión

Ver `PENDIENTES.md` (8ª revisión). Próximo de código acordado: **audit log (#19)**. Sigue bloqueado por la contadora: mapeo PUC, costeo (→ asiento de costo de venta #8), datos maestros.

---

## Sesión — 5 de julio 2026 (2ª parte) — Auditoría de cambios (Claude Fable 5)

### Resumen

Feature **Auditoría de cambios (#19)**: módulo nuevo `auditoria` que registra quién modificó qué en los datos maestros y en las acciones administrativas, con diff campo a campo (antes → después) y pestaña de consulta en Reportes. Tests: 221 → **228 API + 25 componentes**.

### Lo que se hizo

**Backend (`f76ed68`)** — Modelo `RegistroAuditoria` (tabla `auditoria`): fecha UTC, usuario (FK + email como snapshot), acción, entidad, entidad_id, descripción legible y `cambios` (JSON con el diff, solo en updates). `service.py` expone `registrar_auditoria()` (añade a la sesión sin commit: el registro viaja en la misma transacción del cambio — si la operación falla, el log también se revierte) y `diff_cambios()` (compara objeto vs payload, serializa Decimal/fechas/enums, omite campos que no cambian y excluye contraseñas). Endpoints instrumentados: productos y clientes (crear/actualizar/desactivar), proveedores (ídem), parámetros tributarios y de nómina (actualizar/activar/desactivar), toggle de períodos (Cerrar/Reabrir) y usuarios (crear/actualizar/activar/desactivar/reset de contraseña — se registra el hecho, nunca la clave; test lo verifica). Un PUT sin cambios reales no genera registro. `GET /api/v1/auditoria` (Admin/Administradora, 403 para Auxiliar) con filtros por entidad, acción, usuario y rango de fechas. Migración `e8b4d92f7a15`. 7 tests en `test_auditoria.py`.

**Frontend (mismo commit)** — Pestaña "🕵️ Auditoría" en Reportes: filtros (entidad/acción/fechas), badge de color por acción, diff expandible por registro (tachado rojo → verde) y export a Excel. Servicio `auditoriaApi.ts`.

### Pendientes tras esta sesión

Ver `PENDIENTES.md` (9ª revisión). Con #16 y #19 cerrados, lo funcional que queda es: #17 confirmación al cerrar forms con datos sin guardar, #18 RRHH/nómina (Fase 2), #20 Alegra/DIAN, #21 Electron. Bloqueados por la contadora: mapeo PUC, costeo, datos maestros.

---

## Sesión — 5 de julio 2026 (3ª parte) — Confirmación de datos sin guardar (Claude Fable 5)

### Resumen

UX **#17**: ningún formulario con trabajo digitado se descarta ya sin preguntar. Guard global + prop `confirmDiscard` en el Modal compartido + aviso nativo del navegador. Tests: 25 → **30 componentes**; E2E 5/5 local.

### Lo que se hizo

**`7552fc9`** — `utils/unsavedGuard.ts`: registro global de formularios "sucios" con `useUnsavedChanges(dirty)` (activa además `beforeunload` para cierre/recarga del navegador) y `confirmarDescartar()` que consulta la navegación. `Modal.tsx` ganó la prop `confirmDiscard`: la X, el overlay y Escape piden confirmación si hay cambios; el cierre pasa por un ref para que el efecto de foco no se re-ejecute (y robe el foco) cuando el estado dirty cambia al digitar. `App.tsx` confirma antes de cambiar de módulo. El caso que motivó el pendiente — la pestaña **Nueva Compra** con 10 líneas digitadas — quedó protegido en los 3 frentes: cambio de pestaña interna de Compras, cambio de módulo y cierre del navegador. Modales cubiertos: proveedor y devolución (Compras); Nueva Venta, Nueva Cotización, devolución y forms de producto/cliente (Ventas) — los de edición detectan dirty por snapshot JSON del estado inicial. Guardar no pregunta (el submit llama `onClose` directo). 5 tests nuevos (2 Modal + 3 guard).

### Pendientes tras esta sesión

Ver `PENDIENTES.md` (10ª revisión). Funcional restante: #18 RRHH (Fase 2), #20 Alegra/DIAN (necesita token real), #21 Electron, #21a staging, #21b multi-bodega (pregunta de negocio). Bloqueados por la contadora: mapeo PUC, costeo, datos maestros, UVT.

---

## Sesión — 5 de julio 2026 (4ª parte) — Deuda técnica 14c/14d/13a/13b (Claude Fable 5)

### Resumen

Cuatro ítems de deuda técnica en un bloque (`8cd9810`): revocación de sesiones por Admin, smoke E2E en el CI, validación de formato de email y `_enrich_cxc/cxp` explícitos. Tests: 228 → **233 API**; E2E ahora corre local **y** en CI.

### Lo que se hizo

**14c — Revocación de sesiones**: `POST /v1/usuarios/{id}/revocar-sesiones` (solo Admin) borra los refresh tokens del usuario; sin refresh la sesión muere al expirar el access token (máx. 15 min) sin necesidad de desactivar la cuenta. Botón "🔒 Cerrar sesiones" en Usuarios y registro en auditoría. Test verifica que el refresh token revocado devuelve 401.

**14d — Playwright en CI**: job `e2e` en `ci.yml` con `continue-on-error: true` (opcional: no bloquea el merge). `playwright.config.ts` ahora detecta el SO: en Windows usa el python del venv, en Linux (CI) el del sistema — el comando anterior era Windows-only.

**13a — EmailStr**: `ClienteCreate/Update` y `ProveedorCreate/Update` validan formato de email (422 si es inválido); `''` del frontend se normaliza a `None`. Los `Response` se quedan como `str`: los registros legacy con texto libre siguen siendo legibles.

**13b — `_enrich` explícito**: `_enrich_cxc/cxp` construyen `CxCResponse`/`CxPResponse` campo a campo en vez de `{**obj.__dict__}` (frágil ante cambios de modelo y dependiente del estado interno de SQLAlchemy). De paso mypy destapó que `created_at` era Optional en el modelo pero requerido en el schema — corregido.

**Lección aplicada**: esta vez ESLint y mypy se corrieron localmente antes del push (el CI del feature #17 se cayó por una regla de ESLint que no estaba en el checklist local).

### Pendientes tras esta sesión

Ver `PENDIENTES.md` (11ª revisión). La deuda técnica que queda es de mayor calado: #10 migración de nulabilidad legacy (requiere la BD real del servidor), #13 extraer servicios de dominio, #14 manejo de errores consistente en frontend, #14a unificar Cliente/Proveedor/Tercero. Funcional: #18 RRHH, #20 Alegra/DIAN, #21 Electron — todos requieren insumos externos.

---

## Sesión — 5 de julio 2026 (5ª parte) — Errores visibles en frontend (Claude Fable 5)

### Resumen

**#14**: eliminados los `.catch(() => {})` silenciosos del frontend (`c81fcc0`). Antes, si un panel fallaba al cargar, quedaba un vacío indistinguible de "no hay datos"; ahora cada uno muestra un `ErrorState` con el mensaje de qué falló y botón "↻ Reintentar" que recarga sin refrescar la página.

### Lo que se hizo

Componente compartido `components/ErrorState.tsx` (`role="alert"`). Cubiertos 21 sitios: dashboards de Ventas/Compras/Inventario (retry por contador de intento), stock y kardex de Inventario, historial de pagos de Cartera, y las 8 pestañas de Reportes (aging, período, retenciones, P&L, balance, libro diario, auxiliar y auditoría — el patrón es `error` state + `ErrorState onRetry={cargar}`). Los selects de los formularios de captura (clientes/productos en Nueva Venta/Cotización, proveedores/productos en Nueva Compra y Ajuste de inventario) avisan con toast o error visible. Se conservó un único catch silencioso deliberado: las alertas de vencimiento del Dashboard general (documentado en el código — si fallan, el dashboard sigue).

### Pendientes tras esta sesión

Ver `PENDIENTES.md` (12ª revisión). Deuda restante de calado: #10 nulabilidad legacy (necesita la BD real), #13 servicios de dominio, #14a unificar terceros; #12/12a solo aplican multi-worker. Funcional: #18/#20/#21 requieren insumos externos.

---

## Sesión — 5 de julio 2026 (6ª parte) — Release v0.3.0 y auditoría del backlog (Claude Fable 5)

### Resumen

Cierre de la jornada con el **release v0.3.0** (`237bdd8`, tag `v0.3.0`): #11 (`create_all` solo en desarrollo), pulido de UI (módulos 🚧 fuera del menú, búsqueda en Cartera, top morosos en el Dashboard) y extensión de la auditoría a PUC/Centros de Costo. Además, **auditoría completa del backlog**: todos los ítems restantes de `PENDIENTES.md` se verificaron contra el código y se agregaron 4 pendientes nuevos (25-28). Tests: 233 → **234 API**.

### Lo que se hizo

**#11** — con `DEBUG=false` el lifespan ya no ejecuta `create_all`: el esquema en producción lo gobierna solo `alembic upgrade head`. `DESPLIEGUE.md` advierte que el paso es **obligatorio desde v0.3.0** (si se omite: "no such table" en los módulos nuevos). En desarrollo y E2E (`DEBUG=true`) el comportamiento no cambia.

**UI** — Sidebar sin RRHH/Plataformas (las rutas siguen en App.tsx para la Fase 2); buscador en CxC/CxP (número/tercero/NIT/concepto); el panel "Plan de Desarrollo por Fases" del Dashboard es ahora "🔴 Top Clientes Morosos" (top 5 por saldo vencido, sale del aging que ya se cargaba). `APP_VERSION` 0.2.0 → 0.3.0.

**Auditoría PUC/CC** — la revisión detectó que los CRUD de PUC y Centros de Costo no estaban instrumentados (hueco del #19 de la 2ª parte): ahora Crear/Actualizar/Activar/Desactivar quedan en el log con diff, con test propio y las entidades en el filtro de la pestaña.

### Verificación final (todo corrido tras el último cambio)

- Backend: **flake8 OK, mypy 0 errores, 234/234 tests** (5m02s)
- Frontend: **ESLint OK, tsc OK, 30/30 componentes**
- E2E local: **5/5** (valida además que `create_all` gated funciona con `DEBUG=true`)
- CI: verde (ver run del push de `237bdd8`)

### Auditoría del backlog (14ª revisión de PENDIENTES.md)

Cada ítem restante se verificó contra el código (marcas "verificado 2026-07-05" en el archivo): UVT sigue placeholder, no hay `with_for_update`, `confirmar_venta` sigue inline, `cliente_nit` sigue sin FK, el drift de nulabilidad sigue documentado. Pendientes nuevos: **25** editar/eliminar cotizaciones en Borrador, **26** el logout no pasa por el guard de datos sin guardar, **27** revisar manualmente el job E2E del CI en cada release (es `continue-on-error`), **28** purga/archivado del log de auditoría.

### Pendientes tras esta sesión

Ver `PENDIENTES.md` (14ª revisión, todo verificado). Lo de mayor valor ahora: **desplegar v0.3.0 al servidor (#6, con `alembic upgrade head` obligatorio)** y las respuestas de la contadora (#1-4, que desbloquean el asiento de costo #8).

---

## Sesión — 5 de julio 2026 (7ª parte) — Revisión profunda de código y seguridad (Claude Fable 5)

### Resumen

Revisión a profundidad del código (lógica de negocio, flujos cruzados y seguridad) a petición del usuario. Resultado: **3 bugs encontrados y corregidos** (`a24fad4`), **5 hallazgos nuevos al backlog** (pendientes 29-33) y verificación completa final. Tests: 234 → **240 API**.

### Bugs corregidos (BUG-007/008/009)

- **BUG-007 — anulación con devoluciones**: anular una venta que ya tenía notas crédito reingresaba el stock completo de cada línea (la NC ya había reingresado su parte → inventario inflado) y el asiento de la NC quedaba colgado. Igual en compras con ND. Ahora la anulación se bloquea con mensaje claro. Test verifica que el stock queda exactamente como lo dejó la devolución.
- **BUG-008 — cartera huérfana**: anular una venta/compra dejaba su CxC/CxP viva en cartera (un cobro/pago "pendiente" de un documento anulado). Ahora la cartera se anula en cascada con nota `[ANULADA]`; y si ya hay abonos, la anulación exige anular primero los pagos (la plata recibida no puede quedar sin documento).
- **BUG-009 — stock negativo por ajuste**: el ajuste manual de salida no validaba stock disponible — era el único camino que dejaba inventario negativo en silencio (ventas y devoluciones sí validaban). Ahora responde 400.

### Hallazgos que quedaron en PENDIENTES (15ª revisión)

- **29**: las utilidades de impresión inyectan datos sin escapar en `document.write` (XSS almacenado en la ventana de impresión; riesgo bajo en LAN, higiene pendiente).
- **30**: access token en `localStorage` → moverlo a memoria (ya mitigado: 15 min + refresh HttpOnly; documentado en REPORTE_SEGURIDAD).
- **31**: al convertir cotización las retenciones del cliente se aplican en la venta → total menor al cotizado para retenedores (correcto pero sorprende; falta aviso en UI).
- **32**: registrar IP en el log de auditoría.
- **33 (🔐 el más importante)**: `SEED_ADMIN_PASSWORD` tiene default hardcodeado en `config.py` visible en el repo — verificar que el admin del servidor no use esa clave y exigir override por `.env` en producción.

### Lo que se revisó y quedó OK

ORM sin SQL crudo (sin inyección), CORS con validator anti-wildcard, `SECRET_KEY` solo por entorno, refresh tokens rotados y revocables, rate limit en login, bcrypt con truncado explícito, race de numeración documentado (#12a), permisos por rol en endpoints de escritura, EmailStr/DV en escritura, guard de sobreventa en confirmar/devolver.

### Verificación final

flake8 OK · mypy 0 errores · **240/240 tests API** · 30/30 componentes · E2E 5/5 · CI verde (v0.3.0).

---

## Sesión — 5 de julio 2026 (8ª parte) — Hallazgos de seguridad #29 y #33 (Claude Opus 4.8)

### Resumen

Se resolvieron los dos hallazgos de seguridad de la revisión profunda (`cb65d77`): XSS en las utilidades de impresión (#29) y la clave por defecto del admin sembrado (#33). Tests: 240 → **241 API + 32 componentes** (2 nuevos de `esc()`).

### Lo que se hizo

**#29 — XSS en impresión**: nuevo helper `utils/htmlEscape.ts` con `esc()` (escapa `& < > " '`). Aplicado a todo campo de texto libre en las 4 utilidades (`printFactura`, `printCotizacion`, `printCompra`, `printComprobante`): razón social, NIT, observaciones, motivos, notas, concepto, vendedor, ref. proveedor, SKU/nombre de producto, número y estado. Antes se inyectaban crudos en `document.write`, así que un dato guardado con `<script>` se ejecutaba al imprimir (XSS almacenado). Los números (`COP`/`Number`), fechas y constantes de empresa no pasan por `esc()` porque son seguros. 2 tests.

**#33 — clave admin por defecto**: `config.py` gana un validator que rechaza `SEED_ADMIN_PASSWORD` con el valor por defecto (`Admin2026!`, público en el repo) cuando `DEBUG=false` — la app no arranca en producción con la clave conocida. El default se movió a la constante `_DEFAULT_SEED_ADMIN_PASSWORD`. `.env.servidor` trae `SEED_ADMIN_EMAIL/PASSWORD` con nota, y `DESPLIEGUE.md` lo marca obligatorio. Como la suite y el dev corren con `DEBUG=false` (BD real, cookies Secure), se proveyó la clave en 4 frentes: `conftest.py` (os.environ antes de importar la app), el job pytest de CI, el `.env` local (gitignoreado) y `playwright.config.ts` (fija `Admin2026!` para el smoke, que corre con `DEBUG=true`). 1 test siguiendo el patrón del validator de CORS.

### Nota de proceso

El E2E se cayó a la primera: agregar `SEED_ADMIN_PASSWORD` al `.env` cambió la clave del admin sembrado y el smoke seguía usando `Admin2026!`. Se fijó la clave explícitamente en el `env` del webserver de Playwright → E2E determinista e independiente del `.env` del dev.

### Estado

`#33` queda como **33op** en PENDIENTES: el código está resuelto; falta la acción **operativa** (poner la clave propia en el `.env` del servidor y rotarla desde la UI), que es parte del despliegue #6/#7.

### Verificación

flake8 OK · mypy 0 · **241/241 tests API** · 32/32 componentes · E2E 5/5 · pre-commit verde.

---

## Sesión — 6 de julio 2026 — Auditoría con IP (#32) y aviso de retenciones (#31) (Claude Opus 4.8)

### Resumen

Se cerraron los dos últimos hallazgos accionables de la revisión profunda (`40d84df`): la IP del request en el log de auditoría (#32) y el aviso de retenciones al convertir una cotización (#31). Tests: 241 → **242 API**.

### Lo que se hizo

**#32 — IP en auditoría**: `RegistroAuditoria` gana la columna `ip` (String(45), IPv4/IPv6). Un middleware ASGI **puro** (`ClientIPMiddleware`, no `BaseHTTPMiddleware` — este rompe las escrituras async de SQLAlchemy) fija la IP en un `ContextVar` (`auditoria/context.py`) al inicio de cada request; `registrar_auditoria()` la lee sin tener que pasar el `Request` por la firma de los ~18 endpoints instrumentados. La IP se toma de `X-Forwarded-For` (primer salto, por si algún día hay proxy) o del peer directo del scope. Migración `f1a2b3c4d5e6`. La columna IP se muestra en la pestaña Auditoría y va en el export CSV. 1 test (con ASGITransport el host es `testclient`, así que el test valida que el campo se pobló).

**#31 — aviso de retenciones**: `handleConvertir` ahora es async; consulta el perfil del cliente y, si practica retención (fuente/IVA/ICA), el `confirm` avisa que el total de la venta será **menor** que el cotizado (las retenciones se aplican en la factura, no en la cotización). Si no se puede verificar el perfil, convierte igual sin aviso.

### Verificación

flake8 OK · mypy 0 · **242/242 tests API** · 32/32 componentes · E2E 5/5 · pre-commit verde.

### Estado del backlog

Con #31/#32 cerrados, de los hallazgos de la revisión profunda quedan solo cosas menores o dependientes de contexto: #28 purga del log de auditoría y #30 token localStorage→memoria (ambos nice-to-have, #30 ya mitigado), #25 editar cotización en Borrador, #26 logout sin guard, #27 revisar E2E del CI a mano. Lo de mayor valor sigue siendo operativo (desplegar v0.3.0 #6, backups #5) y de negocio (contadora: #1-4 → costo de venta #8).

---

## Sesión — 6 de julio 2026 — El logout pasa por el guard de datos sin guardar (#26) (Claude Opus 4.8)

### Resumen

Se cerró #26: cerrar sesión con un formulario a medias descartaba los cambios sin preguntar. El guard de datos sin guardar (#17) ya cubría el cambio de módulo y el cierre/refresh del navegador, pero **no el logout**. Tests de frontend: 32 → **34 componentes**.

### Lo que se hizo

**#26 — guard en el logout**: `App.tsx` pasaba `onLogout={logout}` (el `logout` crudo del `useAuth()`) directo al `Sidebar`. Se añadió `handleLogout`, que consulta `confirmarDescartar()` antes de cerrar sesión — exactamente el mismo patrón que `handleViewChange` ya usaba para el cambio de módulo (#17) — y la prop pasó a `onLogout={handleLogout}`. Si hay un formulario sucio, el usuario ve el `confirm` de descarte y puede cancelar; si no hay nada sucio, cierra sesión sin fricción.

Test nuevo `frontend/src/App.test.tsx` (primer test a nivel App del repo): mockea `useAuth` y `confirmarDescartar` y stubea las vistas pesadas (DashboardView/HeaderBar/StatusBar) para renderizar barato. Cubre los dos caminos: guard=false → `logout` NO se llama; guard=true → `logout` se llama una vez. 2 tests.

### Verificación

tsc 0 · eslint 0 (App.tsx) · **34/34 componentes** (10 archivos). El backend no se tocó.

### Nota de proceso

Fix hecho con edición directa (no por el pipeline de Hydraia): la sesión se lanzó fuera del repo (System32) y el cambio era un wrapper de 4 líneas sobre un patrón ya existente. Docs actualizados según la regla de mantenimiento: DOCUMENTACION #47, PENDIENTES 18ª revisión (quitado #26), esta bitácora.

---

## Sesión — 6 de julio 2026 — Editar y eliminar cotizaciones en Borrador (#25) (Claude Opus 4.8 · pipeline Hydraia)

### Resumen

Se cerró #25: una cotización en `Borrador` ya se puede **editar** (corregir cabecera e ítems) y **eliminar**. Antes solo había transiciones (enviar/aprobar/rechazar/convertir), así que corregir un borrador con un error obligaba a rechazarlo y crear otro. Primer feature construido con el pipeline Hydraia completo (spec → plan → doble self-review → ejecución → review → verificación). Tests API: 242 → **247**; componentes: 34 → **35**.

### Lo que se hizo

**Backend** (`ventas/router.py`): se extrajo el cálculo de detalles+totales de `create_cotizacion` a un helper compartido `_aplicar_detalles_y_totales(db, cot, data)` (crear y editar no divergen). Dos endpoints nuevos:
- `PUT /cotizaciones/{id}` (`update_cotizacion`): `409` si el estado ≠ Borrador, valida cliente (`404`), recalcula `fecha_vencimiento`, **reemplaza** los detalles (borra los viejos + `db.expire` para refrescar la colección) y recalcula totales; registra auditoría `Actualizar/Cotizacion`.
- `DELETE /cotizaciones/{id}` (`delete_cotizacion`): `409` si el estado ≠ Borrador, registra auditoría `Eliminar/Cotizacion` **antes** de borrar (rastro atómico), y `db.delete` (cascade `delete-orphan` limpia los detalles). Responde `204`.

Ambos usan `CurrentUser` (sin rol especial, como el resto de cotizaciones). El body del PUT reutiliza `CotizacionCreate` (no incluye `estado`/`numero`, así que no se pueden alterar).

**Frontend** (`ventasApi.ts`, `VentasView.tsx`): `updateCotizacion`/`deleteCotizacion`; el modal `NuevaCotizacionModal` acepta una prop opcional `cotizacion` → precarga los campos y hace `PUT` (título "✏️ Editar Cotización", botón "Guardar Cambios") o `POST` (crear). En la fila, **solo en Borrador**, aparecen ✏️ (editar) y 🗑️ (eliminar con `confirm()`).

**Tests**: 5 nuevos en `tests/test_cotizaciones.py` (editar recalcula totales, editar/eliminar no-Borrador → 409, inexistente → 404, eliminar deja auditoría) + `frontend/src/views/CotizacionesEdit.test.tsx` (el modo edición precarga y guarda con `updateCotizacion`).

### Threat model

Superficie: input de usuario autenticado a dos endpoints que mutan/borran un recurso propio. Mitigaciones: guard de estado `409` server-side sobre el registro releído (A01), totales recalculados en backend sin confiar en el cliente (A04), ORM parametrizado (sin inyección), auth por Bearer (sin CSRF), borrado con rastro de auditoría. Sin secretos ni PII nueva.

### Verificación

**247/247 tests API** · **35/35 componentes** · tsc 0 · eslint 0 · pre-commit verde. Backend (ventas/inventario/contabilidad/cartera) sin tocar salvo el módulo cotizaciones.

### Artefactos Hydraia

`docs/hydraia/specs/2026-07-06-editar-eliminar-cotizaciones-borrador-design.md`, `docs/hydraia/plans/2026-07-06-editar-eliminar-cotizaciones-borrador.md`, run log en `docs/hydraia/runs/`.

### Nota de proceso

Pipeline Hydraia ejecutado desde una sesión lanzada en System32 (fuera del repo): la mitad interactiva (spec + plan + aprobaciones) fue normal; la ejecución se hizo con edición directa sobre rutas absolutas en vez de dispatchar subagentes `hydraia-executor`, corriendo los tests reales del repo en cada paso.

## Sesión — 9 de julio 2026

### Resumen

Se resolvió **#28 — purga/archivado del log de auditoría** por el pipeline Hydraia (spec → plan → TDD → doble revisión → verificación). La tabla `auditoria` crecía sin límite; ahora un script programable archiva y depura los registros antiguos de forma segura y trazable.

### Lo que se hizo

**Purga/archivado del log de auditoría (#28)**

- `backend/app/modules/auditoria/purge.py` — `purgar_auditoria(db, corte, archive_dir, encryption_key)`: selecciona los registros con `fecha < corte`, los exporta a JSON **cifrado con Fernet** en `{BACKUP_DIR}/auditoria/auditoria_purga_<fecha>.json.enc`, **verifica** el archivo (descifra y cuenta) y solo entonces ejecuta el `DELETE`. La propia purga se auto-audita (`Purgar/Auditoria`, usuario del sistema). Export-antes-de-borrar → reversible.
- `backend/app/core/config.py` — `AUDITORIA_RETENTION_DAYS = 1825` (~5 años, cubre la firmeza fiscal DIAN; editable por `.env`). Reusa `BACKUP_ENCRYPTION_KEY` + `BACKUP_DIR`.
- `backend/scripts/purge_auditoria.py` — wrapper CLI espejo de `backup_db.py`, para el Programador de tareas de Windows. Registra los modelos como `alembic/env.py` (si no, la relación `RegistroAuditoria→Usuario` no resuelve en un proceso standalone).
- Si falta `BACKUP_ENCRYPTION_KEY` con registros por purgar, aborta sin borrar nada (nunca PII en claro).
- Tests: `backend/tests/test_purge_auditoria.py` (4 async) — viejos borrados / recientes intactos, archivo cifrado descifra a los registros, caso sin registros (no crea archivo), falta de clave (aborta sin borrar).
- Docs: `DESPLIEGUE.md` (tarea programada mensual), `PENDIENTES.md` (20ª rev.), `DOCUMENTACION.md` (item 49).

### Artefactos Hydraia

- Spec: `docs/hydraia/specs/2026-07-09-purga-auditoria-design.md`
- Plan: `docs/hydraia/plans/2026-07-09-purga-auditoria.md`
- QA: `docs/hydraia/qa/2026-07-09-purga-auditoria-cases.md`

### Verificación y PR

- **251 tests** pasan (247 base + 4 nuevos), **mypy** limpio en los archivos nuevos, smoke CLI OK, sin secretos ni dependencias nuevas.
- Rama `feat/28-purga-auditoria` → **PR #9**: https://github.com/leonardeco/superozono-erp/pull/9
- Commits: `fd5a34c` (spec) · `b9594e4` (plan+runlog) · `1078b66` (código) · `949d117` (docs+QA) · `e1f6616` (run log cierre).
