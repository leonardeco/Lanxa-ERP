# Activar Alegra + facturación electrónica DIAN (#20 / #22)

**No requiere Contador.** Requiere cuenta Alegra y (para FE real) resolución DIAN.

## Estado actual del ERP

| Pieza | Estado |
|---|---|
| Código de integración Alegra | ✅ Construido (`/api/v1/alegra/*`) |
| Token en este servidor | ⬜ Vacío hasta que configures `.env` |
| Resolución DIAN en factura impresa | ✅ Bloque listo; vars `DIAN_*` vacías |
| Envío e-factura real | ⬜ Solo con token + numeración autorizada |

Comprobar sin secretos:

```bat
backend\venv\Scripts\python.exe -c "import urllib.request,ssl,json; ctx=ssl._create_unverified_context(); print('usa el ERP logueado o curl con token')"
```

O, con el ERP en marcha y un JWT de Superusuario:

```http
GET https://127.0.0.1:8000/api/v1/alegra/status
Authorization: Bearer <access_token>
```

- Sin token en `.env` → `configurado: false` + lista de pasos (no es error de red).
- Con token válido → `conectado: true` + nombre de empresa Alegra.

## Pasos (orden)

1. **Cuenta Alegra** (Colombia) con plan que incluya API / FE.
2. En Alegra: **Configuración → API** → copiar **token**.
3. En el PC servidor, editar `backend\.env` (nunca subir a Git):

```env
ALEGRA_EMAIL=tu@correo.com
ALEGRA_TOKEN=el-token-de-alegra
```

4. `stop.bat` → `start.bat`.
5. Login Superusuario → probar `GET /api/v1/alegra/status` (o Postman/curl).
6. Sincronizar un cliente de prueba: `POST /api/v1/alegra/sync/cliente/{id}`.
7. Sincronizar un producto: `POST /api/v1/alegra/sync/producto/{id}`.
8. Enviar una venta confirmada: `POST /api/v1/alegra/facturas/{venta_id}` (cuando la resolución DIAN esté activa en Alegra).

## Resolución DIAN en impresión interna (#22)

Aunque la e-factura salga por Alegra, el PDF del ERP puede mostrar la resolución:

```env
DIAN_RESOLUCION_NUMERO=...
DIAN_RESOLUCION_FECHA=YYYY-MM-DD
DIAN_PREFIJO=SETT
DIAN_RANGO_DESDE=1
DIAN_RANGO_HASTA=5000
DIAN_VIGENCIA_HASTA=YYYY-MM-DD
```

Sin estos valores, la impresión indica **documento interno** (correcto para LAN sin FE).

## Seguridad

- No pegar el token en WhatsApp, Excel compartido ni GitHub.
- Si el token se filtra: revocar en Alegra y generar uno nuevo.
- En producción cloud preferir secretos (AWS Secrets Manager); en LAN basta `.env` local.

## Qué no hace este checklist

- Validar PUC ni costeo (Contador).
- Sustituir la autorización DIAN / resolución de numeración (trámites de la empresa).
