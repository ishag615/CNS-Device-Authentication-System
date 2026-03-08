from pathlib import Path
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

def main():
    out_dir = Path("keys")
    out_dir.mkdir(exist_ok=True)

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()

    priv_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pub_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    (out_dir / "device_private.pem").write_bytes(priv_pem)
    (out_dir / "device_public.pem").write_bytes(pub_pem)

    print("Wrote keys/")
    print("  - keys/device_private.pem (keep secret)")
    print("  - keys/device_public.pem")

if __name__ == "__main__":
    main()