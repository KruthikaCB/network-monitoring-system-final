"""
gen_certs.py  –  Generate self-signed CA, server, and client certificates.
Works on Windows, Mac, and Linux — no bash or openssl CLI needed.

Run from the project root:
    python certs/gen_certs.py
"""

import os
import datetime
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa

CERT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)))


def save_key(key, path):
    with open(path, "wb") as f:
        f.write(key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        ))
    print(f"  saved  {path}")


def save_cert(cert, path):
    with open(path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    print(f"  saved  {path}")


def make_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def utcnow():
    return datetime.datetime.now(datetime.timezone.utc)


# ── 1. CA ─────────────────────────────────────────────────────────────────────
print("[*] Generating CA key and certificate...")
ca_key = make_key()
ca_name = x509.Name([
    x509.NameAttribute(NameOID.COUNTRY_NAME,             "IN"),
    x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME,   "Karnataka"),
    x509.NameAttribute(NameOID.LOCALITY_NAME,            "Bengaluru"),
    x509.NameAttribute(NameOID.ORGANIZATION_NAME,        "NMS-CA"),
    x509.NameAttribute(NameOID.COMMON_NAME,              "NMS-RootCA"),
])
ca_cert = (
    x509.CertificateBuilder()
    .subject_name(ca_name)
    .issuer_name(ca_name)
    .public_key(ca_key.public_key())
    .serial_number(x509.random_serial_number())
    .not_valid_before(utcnow())
    .not_valid_after(utcnow() + datetime.timedelta(days=3650))
    .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
    .sign(ca_key, hashes.SHA256())
)
save_key(ca_key,  os.path.join(CERT_DIR, "ca.key"))
save_cert(ca_cert, os.path.join(CERT_DIR, "ca.crt"))

# ── 2. Server cert ────────────────────────────────────────────────────────────
print("[*] Generating server key and certificate...")
srv_key = make_key()
srv_name = x509.Name([
    x509.NameAttribute(NameOID.COUNTRY_NAME,             "IN"),
    x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME,   "Karnataka"),
    x509.NameAttribute(NameOID.LOCALITY_NAME,            "Bengaluru"),
    x509.NameAttribute(NameOID.ORGANIZATION_NAME,        "NMS"),
    x509.NameAttribute(NameOID.COMMON_NAME,              "localhost"),
])
srv_cert = (
    x509.CertificateBuilder()
    .subject_name(srv_name)
    .issuer_name(ca_name)
    .public_key(srv_key.public_key())
    .serial_number(x509.random_serial_number())
    .not_valid_before(utcnow())
    .not_valid_after(utcnow() + datetime.timedelta(days=3650))
    .add_extension(
        x509.SubjectAlternativeName([
            x509.DNSName("localhost"),
            x509.IPAddress(__import__("ipaddress").IPv4Address("127.0.0.1")),
        ]),
        critical=False,
    )
    .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
    .sign(ca_key, hashes.SHA256())
)
save_key(srv_key,  os.path.join(CERT_DIR, "server.key"))
save_cert(srv_cert, os.path.join(CERT_DIR, "server.crt"))

# ── 3. Client cert ────────────────────────────────────────────────────────────
print("[*] Generating client key and certificate...")
cli_key = make_key()
cli_name = x509.Name([
    x509.NameAttribute(NameOID.COUNTRY_NAME,             "IN"),
    x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME,   "Karnataka"),
    x509.NameAttribute(NameOID.LOCALITY_NAME,            "Bengaluru"),
    x509.NameAttribute(NameOID.ORGANIZATION_NAME,        "NMS"),
    x509.NameAttribute(NameOID.COMMON_NAME,              "nms-client"),
])
cli_cert = (
    x509.CertificateBuilder()
    .subject_name(cli_name)
    .issuer_name(ca_name)
    .public_key(cli_key.public_key())
    .serial_number(x509.random_serial_number())
    .not_valid_before(utcnow())
    .not_valid_after(utcnow() + datetime.timedelta(days=3650))
    .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
    .sign(ca_key, hashes.SHA256())
)
save_key(cli_key,  os.path.join(CERT_DIR, "client.key"))
save_cert(cli_cert, os.path.join(CERT_DIR, "client.crt"))

print("\n[+] All certificates generated successfully:")
for f in ["ca.crt", "ca.key", "server.crt", "server.key", "client.crt", "client.key"]:
    path = os.path.join(CERT_DIR, f)
    if os.path.exists(path):
        print(f"  OK  {path}")
