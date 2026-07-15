"""Diagnostico de login local. No imprime secretos completos."""
from __future__ import annotations

import json
import sqlite3
import ssl
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
DB = BACKEND / "superozono.db"
ENV = BACKEND / ".env"
sys.path.insert(0, str(BACKEND))

from app.core.security import verify_password  # noqa: E402


def load_env(path: Path) -> dict[str, str]:
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


def mask(s: str | None) -> str:
    if not s:
        return "(vacio)"
    if len(s) <= 4:
        return "****"
    return s[:3] + "…" + s[-2:] + f" (len={len(s)})"


def try_login(email: str, password: str) -> tuple[int | str, str]:
    ctx = ssl._create_unverified_context()
    body = urlencode({"username": email, "password": password}).encode()
    req = Request(
        "https://127.0.0.1:8000/api/login/access-token",
        data=body,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urlopen(req, context=ctx, timeout=10) as r:
            data = r.read().decode()
            if "access_token" in data:
                return r.status, "OK token"
            return r.status, data[:120]
    except HTTPError as e:
        return e.code, e.read().decode()[:200]
    except URLError as e:
        return "down", str(e.reason)
    except Exception as e:
        return "err", str(e)[:200]


def main() -> int:
    print("=== health ===")
    ctx = ssl._create_unverified_context()
    try:
        with urlopen("https://127.0.0.1:8000/health", context=ctx, timeout=5) as r:
            print(r.read().decode())
    except Exception as e:
        print("API DOWN:", e)

    env = load_env(ENV)
    seed_email = env.get("SEED_ADMIN_EMAIL", "admin@superozonoglobal.com")
    seed_pwd = env.get("SEED_ADMIN_PASSWORD", "")
    print("SEED_ADMIN_EMAIL:", seed_email)
    print("SEED_ADMIN_PASSWORD:", mask(seed_pwd))

    print("=== usuarios en BD ===")
    if not DB.is_file():
        print("NO DB", DB)
        return 1
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "select id, email, rol, is_active, hashed_password, tenant_id from usuarios order by id"
    ).fetchall()
    print("count", len(rows))
    for r in rows:
        print(
            f"  id={r['id']} email={r['email']!r} rol={r['rol']} "
            f"active={r['is_active']} tenant={r['tenant_id']} "
            f"hash={str(r['hashed_password'])[:12]}..."
        )

    # known temps from entrega
    temps = {
        "administradora@superozonoglobal.com": "96HqQaW2di7YBM!",
        "contador@superozonoglobal.com": "73etMaN7zjlei4!",
        "auxiliar@superozonoglobal.com": "S9NiZNeusk8USJ!",
    }
    factory = "Admin2026!"

    print("=== verify_password vs hash en BD ===")
    for r in rows:
        email = r["email"]
        hp = r["hashed_password"]
        checks = []
        if email == seed_email or email == "admin@superozonoglobal.com":
            checks = [
                ("SEED_ADMIN_PASSWORD", seed_pwd),
                ("Admin2026!", factory),
            ]
        if email in temps:
            checks.append(("temp_entrega", temps[email]))
        for label, pwd in checks:
            if not pwd:
                continue
            ok = verify_password(pwd, hp)
            print(f"  {email} + {label}: {ok}")

    print("=== POST /api/login/access-token ===")
    trials = [
        (seed_email, seed_pwd, "seed env"),
        ("admin@superozonoglobal.com", seed_pwd, "admin+seed"),
        ("admin@superozonoglobal.com", factory, "admin+factory"),
        ("administradora@superozonoglobal.com", temps["administradora@superozonoglobal.com"], "admina temp"),
        ("contador@superozonoglobal.com", temps["contador@superozonoglobal.com"], "contador temp"),
        ("auxiliar@superozonoglobal.com", temps["auxiliar@superozonoglobal.com"], "aux temp"),
    ]
    for email, pwd, label in trials:
        code, msg = try_login(email, pwd or "")
        print(f"  [{label}] {email} -> {code} {msg}")

    # frontend env
    fe = ROOT / "frontend" / ".env"
    print("=== frontend .env ===")
    if fe.is_file():
        print(fe.read_text(encoding="utf-8"))
    else:
        print("NO frontend/.env")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
