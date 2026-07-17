"""Smoke diario go-live (LAN). No imprime secretos. Exit 0 = OK.

Chequeos:
  - health
  - login
  - /users/me
  - /v1/ventas/empresa
  - /v1/alegra/status  (informativo si no hay token; --strict-alegra exige conectado)

Uso:
  backend\\venv\\Scripts\\python.exe ops\\smoke-prod.py
  backend\\venv\\Scripts\\python.exe ops\\smoke-prod.py --strict-alegra
  ops\\smoke-diario.bat
"""
from __future__ import annotations

import argparse
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Smoke diario Super Ozono ERP")
    parser.add_argument(
        "--strict-alegra",
        action="store_true",
        help="Falla si Alegra no está configurado o no conecta (por defecto solo informa)",
    )
    parser.add_argument(
        "--base",
        default=BASE,
        help=f"URL base del API (default {BASE})",
    )
    args = parser.parse_args(argv)
    base = args.base.rstrip("/")

    env = _load_env(ENV)
    email = env.get("SEED_ADMIN_EMAIL", "admin@superozonoglobal.com")
    pwd = env.get("SEED_ADMIN_PASSWORD")
    if not pwd:
        print("FAIL: falta SEED_ADMIN_PASSWORD en backend/.env")
        return 1

    ctx = ssl._create_unverified_context()
    fails = 0

    try:
        status, health = _get(f"{base}/health", ctx)
        compact = health.replace(" ", "")
        if status != 200 or ('"status":"ok"' not in compact and "ok" not in health):
            print("FAIL health:", health[:160])
            fails += 1
        else:
            try:
                ver = json.loads(health).get("version", "?")
            except json.JSONDecodeError:
                ver = "?"
            print(f"health: OK (v{ver})")
    except URLError as e:
        print(f"FAIL health: no conecta ({e.reason}). Ejecuta start.bat")
        return 1

    body = urlencode({"username": email, "password": pwd}).encode()
    req = Request(
        f"{base}/api/login/access-token",
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
        st, me = _get(f"{base}/api/users/me", ctx, auth)
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
        st, emp = _get(f"{base}/api/v1/ventas/empresa", ctx, auth)
        if st != 200:
            print(f"ventas/empresa: FAIL HTTP {st}")
            fails += 1
        else:
            nit = json.loads(emp).get("nit", "?")
            print(f"ventas/empresa: OK (nit={nit})")
    except Exception as e:
        print(f"ventas/empresa: FAIL {e}")
        fails += 1

    # Alegra: informativo por defecto
    try:
        st, alg = _get(f"{base}/api/v1/alegra/status", ctx, auth)
        if st != 200:
            print(f"alegra: FAIL HTTP {st}")
            if args.strict_alegra:
                fails += 1
        else:
            body_a = json.loads(alg)
            if body_a.get("conectado"):
                empresa = body_a.get("empresa") or "?"
                print(f"alegra: OK conectado ({empresa})")
            elif body_a.get("configurado") is False:
                print("alegra: no configurado (falta ALEGRA_EMAIL/TOKEN en .env)")
                print("         ver ops/ACTIVAR-ALEGRA-DIAN.md")
                if args.strict_alegra:
                    fails += 1
            else:
                err = body_a.get("error") or body_a.get("mensaje") or "error"
                print(f"alegra: configurado pero no conecta — {err[:120]}")
                if args.strict_alegra:
                    fails += 1
    except Exception as e:
        print(f"alegra: FAIL {e}")
        if args.strict_alegra:
            fails += 1

    if fails:
        print(f"SMOKE: {fails} chequeo(s) fallaron")
        return 1
    print("SMOKE: todo OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
