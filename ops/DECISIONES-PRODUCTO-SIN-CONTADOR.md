# Decisiones de producto (sin Contador) — **confirmadas 2026-07-17**

Confirmadas por el dueño del proyecto al continuar el backlog sin reunión contable
(“sí, continúa con eso”: entrega #7 + cierre de propuestas Electron / multi-bodega).

---

## #21 Electron (.exe) — **DESCARTADO**

| | |
|---|---|
| **Decisión** | No se desarrolla empaquetado Electron |
| **Motivo** | Uso por **navegador en LAN** (HTTPS). Roadmap web/SaaS (ADR multi-tenant + AWS). Un `.exe` duplica build, updates y soporte. |
| **Alternativa** | Acceso directo **Super Ozono ERP** → `start.bat` + Chrome/Edge; o favorito a `https://IP:5173` |
| **Reabrir** | Pedir explícitamente “retomar Electron” |

---

## #21b Multi-bodega — **NO en v0.3 / fuera de alcance actual**

| | |
|---|---|
| **Decisión** | Una sola bodega / un stock por producto |
| **Motivo** | LAN mono-empresa; multi-bodega implica transferencias, reportes por almacén y costeo (Contador). |
| **Reabrir** | Definir número de bodegas, transferencias y reglas de costeo |

---

## #18 RRHH / nómina

Sin cambio: Fase 2. Solo parámetros de nómina en UI. Requiere definiciones de negocio.

---

## Registro

| Fecha | Acción |
|---|---|
| 2026-07-17 | Propuestas documentadas |
| 2026-07-17 | Confirmadas al continuar entrega #7 + descarte Electron/multi-bodega |
