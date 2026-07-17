# HOY — Ejecutar entrega #7 (Superusuario)

Guía de **una página** para repartir accesos. Detalle: `ENTREGA-7-USUARIOS.md`.

## 1. Preflight (2 min, PC servidor)

```bat
ops\preflight-entrega-7.bat
```

o:

```bat
backend\venv\Scripts\python.exe ops\preflight-entrega-7.py
```

Esperado: `RESULTADO: listo para repartir tarjetas`.  
Si falla: `start.bat` y reintenta.

URL: **https://192.168.1.131:5173**

## 2. Carpeta del Escritorio

`Entrega-SuperOzono-v030\`

| Archivo | Uso |
|---|---|
| `INICIO.txt` | Orden general |
| `01` … `07-*.txt` | Tarjeta por persona (en mano, no por chat) |
| `superozono-ca.crt` | Instalar en cada PC cliente (una vez) |
| `CHECKLIST-CAMBIO-CLAVES.txt` | Marcar cuando cambien clave |
| `MANUAL-DE-USUARIO.md` | Entregar o dejar en red |

## 3. Por cada persona (5–7 min)

1. Entregar tarjeta en mano.
2. En su PC (primera vez HTTPS):

```bat
certutil -user -addstore Root superozono-ca.crt
```

3. Abrir la URL → login con correo + clave temporal.
4. **Cambiar contraseña** (Usuarios / Cambiar mi contraseña).
5. Marcar checklist.
6. Confirmar que ve sus módulos.

## 4. Cierre del día

- [ ] 7 tarjetas entregadas  
- [ ] 7 contraseñas cambiadas  
- [ ] Borrar `CREDENCIALES-TEMPORALES*` del Escritorio y de `C:\SuperOzono-Backups` si hay copias  
- [ ] Avisar al equipo de desarrollo / anotar en `PENDIENTES.md`: **#7 cerrado**

## 5. Si no pueden entrar

| Problema | Acción |
|---|---|
| No carga | En servidor: `start.bat` |
| Certificado | Reinstalar CA |
| 429 | Esperar 1 min |
| Olvidó clave | Superusuario resetea en Usuarios |

## Relacionado

- Seguridad: `ops/SEGURIDAD-LAN.md`
- Contador (después): Escritorio `Entrega-Contador-PUC\`
