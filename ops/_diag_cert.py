"""Cert SAN listing for ops/diagnostico.ps1 — no secrets."""
import sys
from pathlib import Path

from cryptography import x509

if len(sys.argv) < 2:
    print("FAIL sin path de cert")
    sys.exit(1)

p = Path(sys.argv[1])
if not p.exists():
    print("FAIL sin server.crt")
    sys.exit(1)

c = x509.load_pem_x509_certificate(p.read_bytes())
sans = c.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
print("SAN: " + ", ".join(str(getattr(x, "value", x)) for x in sans))
