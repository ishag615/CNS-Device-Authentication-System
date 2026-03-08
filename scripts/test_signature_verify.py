#!/usr/bin/env python3
import base64
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

DB_PATH = Path("data/iot_auth.db")
DEVICE_ID = "test_device"
PRIVATE_KEY_PATH = Path("keys/device_private.pem")


def load_public_key_from_db(device_id: str):
    con = sqlite3.connect(DB_PATH)
    try:
        row = con.execute(
            "SELECT public_key_pem FROM devices WHERE device_id = ?",
            (device_id,),
        ).fetchone()
    finally:
        con.close()

    if not row:
        raise SystemExit(f"Device not found in DB: {device_id}")

    public_key_pem = row[0].encode("utf-8")
    return serialization.load_pem_public_key(public_key_pem)


def load_private_key():
    return serialization.load_pem_private_key(
        PRIVATE_KEY_PATH.read_bytes(),
        password=None,
    )


def sign_message(private_key, message: bytes) -> bytes:
    return private_key.sign(
        message,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH,
        ),
        hashes.SHA256(),
    )


def verify_signature(public_key, message: bytes, signature: bytes) -> bool:
    try:
        public_key.verify(
            signature,
            message,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH,
            ),
            hashes.SHA256(),
        )
        return True
    except Exception:
        return False


def main():
    if not DB_PATH.exists():
        raise SystemExit(f"Missing DB at {DB_PATH}. Run: python scripts/setup_database.py")
    if not PRIVATE_KEY_PATH.exists():
        raise SystemExit(f"Missing private key at {PRIVATE_KEY_PATH}. Run key generation first.")

    # Message we pretend the device is authenticating with
    nonce = "abc123"
    ts = datetime.now(timezone.utc).isoformat()
    message = f"{DEVICE_ID}|{nonce}|{ts}".encode("utf-8")

    private_key = load_private_key()
    public_key = load_public_key_from_db(DEVICE_ID)

    signature = sign_message(private_key, message)

    print("Message:", message.decode("utf-8"))
    print("Signature (b64):", base64.b64encode(signature).decode("utf-8")[:60] + "...")

    ok = verify_signature(public_key, message, signature)
    print("\nvalid - Verify (original message):", ok)

    # Tamper test (attacker would try to modify something with a seemingly valid message)
    tampered = f"{DEVICE_ID}|{nonce}|{ts}|tamperedValue".encode("utf-8")
    ok2 = verify_signature(public_key, tampered, signature)
    print("invalid - Verify (tampered message):", ok2)

    print("\nDone.")


if __name__ == "__main__":
    main()