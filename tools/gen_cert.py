"""
Generate a self-signed TLS certificate for the local Blaze TLS listener
(config/certs/server.crt + server.key). The client may reject it; the
listener is optional and mainly useful for observing TLS ClientHellos.
"""

from pathlib import Path
from datetime import datetime, timedelta, timezone

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def main():
    cert_dir = Path(__file__).resolve().parent.parent / "config" / "certs"
    cert_dir.mkdir(parents=True, exist_ok=True)
    cert_path = cert_dir / "server.crt"
    key_path = cert_dir / "server.key"

    if cert_path.exists() and key_path.exists():
        print(f"Cert already exists: {cert_path}")
        return

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    name = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "winter15.gosredirector.ea.com"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "FIFA 16 Revival"),
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
        .add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName("winter15.gosredirector.ea.com"),
                x509.DNSName("winter15.gosredirector.scert.ea.com"),
                x509.DNSName("localhost"),
                x509.IPAddress(__import__("ipaddress").IPv4Address("127.0.0.1")),
            ]),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )

    key_path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        )
    )
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))

    print(f"Wrote {cert_path}")
    print(f"Wrote {key_path}")


if __name__ == "__main__":
    main()
