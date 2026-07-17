"""Health check for ops/diagnostico.ps1 — no secrets."""
import json
import ssl
import sys
from urllib.request import urlopen

ctx = ssl._create_unverified_context()
last = None
for base in ("https://127.0.0.1:8000", "https://localhost:8000"):
    try:
        with urlopen(base + "/health", context=ctx, timeout=4) as r:
            d = json.loads(r.read().decode())
        print(
            "OK %s status=%s v=%s db=%s"
            % (base, d.get("status"), d.get("version"), d.get("database"))
        )
        sys.exit(0)
    except Exception as e:
        last = e
print("FAIL %s" % last)
sys.exit(1)
