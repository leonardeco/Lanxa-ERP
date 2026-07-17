"""
Preflight #7 — verifica que el ERP este listo para repartir accesos.
No imprime contrasenas ni secretos.

Uso (ERP preferiblemente arrancado):
  backend\\venv\\Scripts\\python.exe ops\\preflight-entrega-7.py
"""
from __future__ import annotations

import json
import os
import sqlite3
import ssl
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
DB = BACKEND / "superozono.db"
DESKTOP = Path(os.environ.get("USERPROFILE", "")) / "Desktop" / "Entrega-SuperOzono-v030"

EXPECTED = [
    ("admin@superozonoglobal.com", "Superusuario"),
    ("directora@superozonoglobal.com", "Directora"),
    ("ceo@superozonoglobal.com", "CEO"),
    ("contador@superozonoglobal.com", "Contador"),
    ("auxiliar1@superozonoglobal.com", "Auxiliar Contable"),
    ("auxiliar2@superozonoglobal.com", "Auxiliar Contable"),
    ("auxiliar3@superozonoglobal.com", "Auxiliar Contable"),
]

CARDS = [
    "01-SUPERUSUARIO.txt",
    "02-DIRECTORA.txt",
    "03-CEO.txt",
    "04-CONTADOR.txt",
    "05-AUXILIAR1.txt",
    "06-AUXILIAR2.txt",
    "07-AUXILIAR3.txt",
    "INICIO.txt",
    "superozono-ca.crt",
    "CHECKLIST-CAMBIO-CLAVES.txt",
]

fail = 0


def ok(msg: str) -> None:
    print(f"  [OK] {msg}")


def bad(msg: str) -> None:
    global fail
    fail += 1
    print(f"  [X]  {msg}")


def warn(msg: str) -> None:
    print(f"  [!!] {msg}")


def main() -> int:
    print("=== Preflight #7 Entrega usuarios ===")
    print(f"Repo: {ROOT}")
    print()

    # 1 BD usuarios
    print("--- 1 Usuarios en BD ---")
    if not DB.exists():
        bad(f"No existe {DB}")
    else:
        con = sqlite3.connect(DB)
        con.row_factory = sqlite3.Row
        rows = con.execute(
            "SELECT email, rol, is_active FROM usuarios"
        ).fetchall()
        by_email = {str(r["email"]).lower(): r for r in rows}
        ok(f"{len(rows)} usuario(s) en BD")
        for email, rol_hint in EXPECTED:
            r = by_email.get(email.lower())
            if not r:
                bad(f"Falta usuario {email}")
                continue
            if not r["is_active"]:
                bad(f"Inactivo: {email}")
                continue
            # rol flexible (auxiliar naming)
            rol = str(r["rol"])
            if rol_hint == "Auxiliar Contable":
                if "Auxiliar" not in rol:
                    warn(f"{email} rol={rol} (esperado Auxiliar*)")
                else:
                    ok(f"{email} · {rol}")
            elif rol != rol_hint and rol_hint not in rol:
                warn(f"{email} rol={rol} (esperado ~{rol_hint})")
                ok(f"{email} activo")
            else:
                ok(f"{email} · {rol}")

    # 2 Paquete escritorio
    print()
    print("--- 2 Paquete Escritorio ---")
    if not DESKTOP.is_dir():
        bad(f"No existe carpeta {DESKTOP}")
    else:
        ok(f"Carpeta: {DESKTOP}")
        for name in CARDS:
            p = DESKTOP / name
            if p.exists():
                ok(name)
            else:
                bad(f"Falta {name}")
        # IP en tarjetas
        sample = DESKTOP / "INICIO.txt"
        if sample.exists():
            text = sample.read_text(encoding="utf-8", errors="replace")
            if "192.168.1.48" in text:
                bad("INICIO.txt aun tiene IP antigua .48 — actualiza a .131")
            elif "192.168.1.131" in text or "5173" in text:
                ok("INICIO.txt tiene URL con puerto 5173")
            else:
                warn("INICIO.txt sin IP reconocible")

    # 3 CA en repo
    print()
    print("--- 3 Certificado CA ---")
    ca = ROOT / "certs" / "superozono-ca.crt"
    if ca.exists():
        ok("certs/superozono-ca.crt")
    else:
        bad("Falta certs/superozono-ca.crt")

    # 4 Health API + version
    print()
    print("--- 4 Health API ---")
    ctx = ssl._create_unverified_context()
    health_ok = False
    api_version = None
    last: Exception | str = "sin intento"
    for base in ("https://127.0.0.1:8000", "https://localhost:8000"):
        try:
            with urlopen(base + "/health", context=ctx, timeout=4) as r:
                data = json.loads(r.read().decode())
            api_version = data.get("version")
            ok(f"{base} status={data.get('status')} v={api_version}")
            health_ok = True
            break
        except (URLError, HTTPError, TimeoutError, OSError) as e:
            last = e
    if not health_ok:
        bad(f"API no responde — ejecuta start.bat ({last})")
    else:
        # Alinear con frontend APP_VERSION (config.ts) sin importar TS
        fe_cfg = ROOT / "frontend" / "src" / "config.ts"
        if fe_cfg.exists() and api_version:
            txt = fe_cfg.read_text(encoding="utf-8", errors="replace")
            m = __import__("re").search(r"APP_VERSION\s*=\s*['\"]([^'\"]+)['\"]", txt)
            if m:
                fe_ver = m.group(1)
                if str(api_version) == fe_ver:
                    ok(f"Versiones alineadas API=FE={fe_ver}")
                else:
                    warn(f"Version mismatch API={api_version} FE={fe_ver} — actualizar config.ts/config.py")

    # 5 Frontend env IP
    print()
    print("--- 5 frontend.env ---")
    fe = ROOT / "frontend" / ".env"
    if fe.exists():
        line = next(
            (ln for ln in fe.read_text(encoding="utf-8", errors="replace").splitlines() if ln.startswith("VITE_API_URL=")),
            "",
        )
        if line:
            if "192.168.1.48" in line:
                bad("frontend.env IP antigua .48")
            else:
                ok(line)
        else:
            warn("Sin VITE_API_URL")
    else:
        warn("Sin frontend/.env")

    print()
    if fail == 0:
        print("RESULTADO: listo para repartir tarjetas (#7)")
        print(f"Paquete: {DESKTOP}")
        print("Siguiente: seguir ops/ENTREGA-7-USUARIOS.md (humano)")
        return 0
    print(f"RESULTADO: {fail} problema(s) — no repartas hasta corregir")
    return 1


if __name__ == "__main__":
    sys.exit(main())
