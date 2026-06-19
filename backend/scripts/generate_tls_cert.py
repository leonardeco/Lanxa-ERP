"""
Genera (si no existen) una CA local autofirmada y un certificado de servidor
para HTTPS interno en la LAN. Uvicorn y Vite lo usan desde certs/.

Uso: venv\\Scripts\\python.exe scripts\\generate_tls_cert.py [host ...]
Sin argumentos, usa el host de frontend\\.env (VITE_API_URL) + localhost/127.0.0.1.

La CA (certs\\superozono-ca.crt) hay que instalarla como confiable en cada PC
que vaya a usar el ERP (ver DOCUMENTACION.md, sección HTTPS). El certificado
de servidor se puede regenerar sin tocar los PCs clientes, mientras la CA no
cambie.
"""
import ipaddress
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CERTS_DIR = REPO_ROOT / "certs"
CA_KEY = CERTS_DIR / "superozono-ca.key"
CA_CERT = CERTS_DIR / "superozono-ca.crt"
SERVER_KEY = CERTS_DIR / "server.key"
SERVER_CERT = CERTS_DIR / "server.crt"


def _default_hosts() -> list[str]:
    hosts = ["localhost", "127.0.0.1"]
    env_file = REPO_ROOT / "frontend" / ".env"
    if env_file.exists():
        match = re.search(r"^VITE_API_URL=https?://([^:/]+)", env_file.read_text(encoding="utf-8"), re.MULTILINE)
        if match and match.group(1) not in hosts:
            hosts.insert(0, match.group(1))
    return hosts


def _san_entry(host: str):
    try:
        return x509.IPAddress(ipaddress.ip_address(host))
    except ValueError:
        return x509.DNSName(host)


def _generate_ca():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "Super Ozono ERP - CA Local"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Super Ozono Global"),
    ])
    now = datetime.now(timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=3650))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(
            x509.KeyUsage(
                key_cert_sign=True, crl_sign=True, digital_signature=True,
                content_commitment=False, key_encipherment=False, data_encipherment=False,
                key_agreement=False, encipher_only=False, decipher_only=False,
            ),
            critical=True,
        )
        .sign(key, hashes.SHA256())
    )
    return key, cert


def _generate_server_cert(ca_key, ca_cert, hosts: list[str]):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, hosts[0]),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Super Ozono Global"),
    ])
    now = datetime.now(timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(ca_cert.subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=825))  # limite que aceptan los navegadores para hojas
        .add_extension(x509.SubjectAlternativeName([_san_entry(h) for h in hosts]), critical=False)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True, key_encipherment=True, content_commitment=False,
                data_encipherment=False, key_agreement=False, key_cert_sign=False,
                crl_sign=False, encipher_only=False, decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
        .sign(ca_key, hashes.SHA256())
    )
    return key, cert


def main() -> None:
    hosts = sys.argv[1:] or _default_hosts()
    CERTS_DIR.mkdir(exist_ok=True)

    if CA_KEY.exists() and CA_CERT.exists():
        ca_key = serialization.load_pem_private_key(CA_KEY.read_bytes(), password=None)
        ca_cert = x509.load_pem_x509_certificate(CA_CERT.read_bytes())
        print(f"Usando CA local existente: {CA_CERT}")
    else:
        ca_key, ca_cert = _generate_ca()
        CA_KEY.write_bytes(ca_key.private_bytes(
            serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
        ))
        CA_CERT.write_bytes(ca_cert.public_bytes(serialization.Encoding.PEM))
        print(f"CA local generada: {CA_CERT}")

    server_key, server_cert = _generate_server_cert(ca_key, ca_cert, hosts)
    SERVER_KEY.write_bytes(server_key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    ))
    SERVER_CERT.write_bytes(server_cert.public_bytes(serialization.Encoding.PEM))
    print(f"Certificado de servidor generado para {hosts}: {SERVER_CERT}")
    print()
    print(f"IMPORTANTE: instalar {CA_CERT} como 'confiable' en cada PC que use el ERP.")


if __name__ == "__main__":
    main()
