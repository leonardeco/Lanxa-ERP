# #7 — Entrega de accesos a 7 usuarios (lista para ejecutar)

**Estado:** lista operativa. Antes estaba aplazada a propósito; este documento es el
**plan de ejecución** cuando decidas repartir accesos.

**Paquete físico:** Escritorio → `Entrega-SuperOzono-v030\`  
**URL app:** `https://192.168.1.48:5173`  
**Servidor:** acceso directo **Super Ozono ERP** (`start.bat`)

---

## Antes de empezar (5 min)

- [ ] ERP arrancado y smoke OK:

```bat
backend\venv\Scripts\python.exe ops\smoke-prod.py
```

- [ ] Carpeta `Entrega-SuperOzono-v030` en el Escritorio (tarjetas 01–07)
- [ ] Copia actualizada del manual (recomendado):

```bat
copy /Y MANUAL-DE-USUARIO.md "%USERPROFILE%\Desktop\Entrega-SuperOzono-v030\"
```

- [ ] CA lista para PCs cliente: `certs\superozono-ca.crt` (también en la carpeta de entrega)

---

## Usuarios y tarjetas

| # | Rol | Correo | Tarjeta |
|---|---|---|---|
| 1 | Superusuario | admin@superozonoglobal.com | `01-SUPERUSUARIO.txt` |
| 2 | Directora | directora@superozonoglobal.com | `02-DIRECTORA.txt` |
| 3 | CEO | ceo@superozonoglobal.com | `03-CEO.txt` |
| 4 | Contador | contador@superozonoglobal.com | `04-CONTADOR.txt` |
| 5 | Auxiliar Contable 1 | auxiliar1@superozonoglobal.com | `05-AUXILIAR1.txt` |
| 6 | Auxiliar Contable 2 | auxiliar2@superozonoglobal.com | `06-AUXILIAR2.txt` |
| 7 | Auxiliar Contable 3 | auxiliar3@superozonoglobal.com | `07-AUXILIAR3.txt` |

Credenciales temporales: solo en las tarjetas / archivos de la carpeta de entrega  
(**no** en Git, **no** en chat).

---

## Por cada persona (5–7 min)

1. **Entregar en mano** (o sobre cerrado):
   - Tarjeta `0N-….txt`
   - `MANUAL-DE-USUARIO.md` (o resumen impreso)
   - URL: `https://192.168.1.48:5173`
2. **En su PC** (si es la primera vez con HTTPS local):

```bat
certutil -user -addstore Root superozono-ca.crt
```

(usar la CA de la carpeta de entrega)

3. Login con correo + clave temporal de la tarjeta.
4. **Cambiar contraseña de inmediato**  
   (Usuarios & Accesos, o el flujo de cambio de clave).  
   Mínimo 8 caracteres, letra + dígito. **No** reutilizar la temporal.
5. Marcar en `CHECKLIST-CAMBIO-CLAVES.txt` de la carpeta de entrega.
6. Confirmar que ve los módulos de su rol (tabla del manual §1).

### Quién puede anular documentos

Solo **Superusuario** y **Directora**. El resto opera sin anular.

---

## Checklist de cierre (#7)

- [ ] 7 personas recibieron tarjeta + manual + URL  
- [ ] 7 personas cambiaron contraseña  
- [ ] 7 personas entraron al menos una vez  
- [ ] Borrar del Escritorio (y de Backups si aplica):
  - `CREDENCIALES-TEMPORALES.txt`
  - `CREDENCIALES-ESTRUCTURA-USUARIOS.txt`
  - copias `CREDENCIALES-*-NO-SUBIR.txt` en `C:\SuperOzono-Backups`
- [ ] (Opcional) Guardar solo un registro interno “quién tiene acceso” **sin** claves

Cuando lo anterior esté marcado → **#7 cerrado** (anotar en `PENDIENTES.md` + bitácora).

---

## Si alguien no puede entrar

| Síntoma | Acción |
|---|---|
| No conecta al servidor | En el PC servidor: `start.bat` |
| Certificado no confiable | Reinstalar CA (`certutil` arriba) |
| 429 demasiados intentos | Esperar 1 minuto |
| Olvidó la clave nueva | Superusuario → Usuarios → restablecer contraseña |
| Correo/nombre real distinto | Superusuario edita en Usuarios & Accesos |

---

## Relacionado

- Checklist diario: `ops/CHECKLIST-GO-LIVE-DIARIO.md`
- Estado PC: `ops/ESTADO-OPERATIVO-PC.md`
- Paquete Contador (PUC, **después**): Escritorio `Entrega-Contador-PUC\`
