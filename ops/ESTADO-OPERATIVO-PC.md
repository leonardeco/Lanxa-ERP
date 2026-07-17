# Estado operativo — este PC servidor

**Verificado:** 2026-07-17 (sesión cierre docs + login UI)  
**Código:** `main` v0.3.0 — arranque estable con sync IP

## Producción LAN (ahora)

| Componente | Estado | Detalle |
|---|---|---|
| Backend | ON (si start.bat activo) | `https://192.168.1.131:8000` / health v0.3.0 |
| Frontend | ON | `https://192.168.1.131:5173` |
| Login Superusuario | OK | `admin@superozonoglobal.com` (verificado API + UI) |
| BD SQLite LAN | OK | `backend\superozono.db` |
| IP LAN | **192.168.1.131** | Auto-sync: `ops\sync-lan-ip.ps1` al `start.bat` |
| CA confiable | OK | `certs\superozono-ca.crt` en Root usuario |
| Acceso escritorio | OK | Super Ozono ERP → start.bat |
| Postgres (tests) | Running | `postgresql-x64-17` / BD `superozono_test` |
| Smoke diario | Tarea 08:00 | `SuperOzonoERP-SmokeDiario` + `ops\smoke-diario.bat` |

## Arranque / parada

1. Doble clic **Super Ozono ERP** o `start.bat` (sincroniza IP + valida .env UTF-8 + espera health).
2. Parar: `stop.bat` o cerrar ventanas Backend/Frontend.
3. Si la IP cambia: `start.bat` de nuevo (o `ops\sync-lan-ip.ps1`).
4. Smoke: `ops\smoke-diario.bat`

## Entrega usuarios (#7)

Guía: `ops\ENTREGA-7-USUARIOS.md`  
Paquete: Escritorio `Entrega-SuperOzono-v030\`

## Backups (#5)

Offsite OneDrive OK. Clave en `backend\.env` + gestor (sin plaintext en carpeta backups).

## No bloquea ops diarias

- Contador: validación PUC / costeo / asiento costo de venta.
- Alegra: falta token real.
- Entrega #7: acción humana de repartir tarjetas.

## Docs

- Pendientes: `PENDIENTES.md` (44ª+ rev)
- Bitácora: `BITACORA.md`
- Checklist diario: `ops\CHECKLIST-GO-LIVE-DIARIO.md`
- Seguridad: `ops\SEGURIDAD-LAN.md`
- Readiness: `ops\PRODUCTION-READINESS-LAN.md`
