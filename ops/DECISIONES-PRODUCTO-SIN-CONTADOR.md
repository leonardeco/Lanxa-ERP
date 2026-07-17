# Decisiones de producto (sin Contador) — propuestas 2026-07-17

Registro de **propuestas** para no dejar el backlog en limbo.  
Se pueden revertir cuando el dueño del negocio diga lo contrario.

---

## #21 Electron (.exe) — **propuesta: DESCARTAR para v0.3 / SaaS**

| | |
|---|---|
| **Decisión propuesta** | No invertir en empaquetado Electron |
| **Motivo** | El ERP ya se usa por **navegador en LAN** (HTTPS). El roadmap apunta a **web/SaaS** (ADR multi-tenant + AWS). Un `.exe` duplica costo de build, updates y soporte. |
| **Qué se usa en su lugar** | Acceso directo de escritorio → `start.bat` + Edge/Chrome; o favorito a `https://IP:5173` |
| **Estado en backlog** | Candidato a cerrar como “no planificado” hasta nueva orden |
| **Cómo reabrir** | Pedir explícitamente “retomar Electron” |

---

## #21b Multi-bodega — **propuesta: NO en LAN v0.3**

| | |
|---|---|
| **Decisión propuesta** | Una sola bodega / un solo stock por producto |
| **Motivo** | Super Ozono opera mono-empresa LAN; multi-bodega implica modelo de stock, transferencias y reportes por almacén. |
| **Estado** | Fuera de alcance de v0.3.0 |
| **Cómo reabrir** | Definir: ¿cuántas bodegas? ¿transferencias? ¿costeo por bodega? (ahí sí entra Contador) |

---

## #18 RRHH / nómina — **sin cambio**

Sigue en Fase 2. Solo parámetros de nómina en UI. No se inventan liquidaciones sin definiciones de negocio (y Contador/abogado laboral).

---

## Cómo confirmar estas propuestas

- **Confirmar:** “OK, descarta Electron y multi-bodega” → se cierra en `PENDIENTES.md` y `DOCUMENTACION.md` §13.
- **Rechazar:** “Queremos Electron” o “sí multi-bodega” → se reabre el ítem con alcance.
