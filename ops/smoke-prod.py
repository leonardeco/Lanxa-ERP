"""Smoke go-live local (LAN). No imprime secretos. Exit 0 = OK.

Comprueba: health, login, /users/me, /v1/ventas/empresa.
Uso: backend\\venv\\Scripts\\python.exe ops\\smoke-prod.py
"""
from __future__ import annotations

import json
import ssl
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
ENV = ROOT / "backend" / ".env"
BASE = "https://127.0.0.1:8000"


def _load_env(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def _get(url: str, ctx: ssl.SSLContext, headers: dict | None = None) -> tuple[int, str]:
    req = Request(url, method="GET", headers=headers or {})
    with urlopen(req, context=ctx, timeout=15) as r:
        return r.status, r.read().decode()


def main() -> int:
    env = _load_env(ENV)
    email = env.get("SEED_ADMIN_EMAIL", "admin@superozonoglobal.com")
    pwd = env.get("SEED_ADMIN_PASSWORD")
    if not pwd:
        print("FAIL: falta SEED_ADMIN_PASSWORD en backend/.env")
        return 1

    ctx = ssl._create_unverified_context()
    fails = 0

    try:
        status, health = _get(f"{BASE}/health", ctx)
        compact = health.replace(" ", "")
        if status != 200 or ('"status":"ok"' not in compact and "ok" not in health):
            print("FAIL health:", health[:160])
            fails += 1
        else:
            print("health: OK")
    except URLError as e:
        print(f"FAIL health: no conecta ({e.reason}). Ejecuta start.bat")
        return 1

    body = urlencode({"username": email, "password": pwd}).encode()
    req = Request(
        f"{BASE}/api/login/access-token",
        data=body,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urlopen(req, context=ctx, timeout=15) as r:
            data = r.read().decode()
            status = r.status
    except HTTPError as e:
        print(f"login: FAIL HTTP {e.code}")
        return 1
    except URLError as e:
        print(f"login: FAIL {e.reason}")
        return 1

    token = None
    if status == 200 and "access_token" in data:
        try:
            token = json.loads(data).get("access_token")
        except json.JSONDecodeError:
            token = None
        print(f"login: OK ({email})")
    else:
        print(f"login: FAIL status={status}")
        return 1

    if not token:
        print("FAIL: sin access_token en respuesta de login")
        return 1

    auth = {"Authorization": f"Bearer {token}"}
    try:
        st, me = _get(f"{BASE}/api/users/me", ctx, auth)
        if st != 200:
            print(f"users/me: FAIL HTTP {st}")
            fails += 1
        else:
            rol = json.loads(me).get("rol", "?")
            print(f"users/me: OK (rol={rol})")
    except Exception as e:
        print(f"users/me: FAIL {e}")
        fails += 1

    try:
        st, emp = _get(f"{BASE}/api/v1/ventas/empresa", ctx, auth)
        if st != 200:
            print(f"ventas/empresa: FAIL HTTP {st}")
            fails += 1
        else:
            nit = json.loads(emp).get("nit", "?")
            print(f"ventas/empresa: OK (nit={nit})")
    except Exception as e:
        print(f"ventas/empresa: FAIL {e}")
        fails += 1

    if fails:
        print(f"SMOKE: {fails} chequeo(s) fallaron")
        return 1
    print("SMOKE: todo OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
