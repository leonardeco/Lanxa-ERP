"""Smoke login prod local. No imprime secretos. Exit 0 = OK."""
from __future__ import annotations

import ssl
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
ENV = ROOT / "backend" / ".env"


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


def main() -> int:
    env = _load_env(ENV)
    email = env.get("SEED_ADMIN_EMAIL", "admin@superozonoglobal.com")
    pwd = env.get("SEED_ADMIN_PASSWORD")
    if not pwd:
        print("FAIL: falta SEED_ADMIN_PASSWORD en backend/.env")
        return 1

    ctx = ssl._create_unverified_context()
    # health
    with urlopen("https://127.0.0.1:8000/health", context=ctx, timeout=15) as r:
        health = r.read().decode()
    if '"status":"ok"' not in health.replace(" ", ""):
        # tolerar espacios en JSON
        if '"status"' not in health or "ok" not in health:
            print("FAIL health:", health[:120])
            return 1
    print("health: OK")

    body = urlencode({"username": email, "password": pwd}).encode()
    req = Request(
        "https://127.0.0.1:8000/api/login/access-token",
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

    if status == 200 and "access_token" in data:
        print(f"login: OK ({email})")
        return 0
    print(f"login: FAIL status={status}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
