#!/usr/bin/env python3
import argparse, base64, sys
from pathlib import Path
from datetime import datetime, timezone
import httpx

from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding

GATEWAY = "http://127.0.0.1:8000"


def load_private_key(path: Path):
    return serialization.load_pem_private_key(path.read_bytes(), password=None)


def sign(private_key, msg: bytes) -> bytes:
    return private_key.sign(
        msg,
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
        hashes.SHA256(),
    )


def check(condition: bool, pass_msg: str, fail_msg: str):
    if condition:
        print(f"PASS: {pass_msg}")
    else:
        print(f"FAIL: {fail_msg}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--device-id", default="test_device")
    ap.add_argument("--public-key", default="keys/device_public.pem")
    ap.add_argument("--private-key", default="keys/device_private.pem")
    ap.add_argument("--mode", choices=["normal", "forge", "replay"], default="normal")
    args = ap.parse_args()

    pub_path = Path(args.public_key)
    priv_path = Path(args.private_key)

    if not pub_path.exists():
        print(f"Missing public key file: {pub_path}")
        print("   Run: python3 scripts/generate_device_keys.py")
        sys.exit(1)

    if not priv_path.exists():
        print(f"Missing private key file: {priv_path}")
        print("   Run: python3 scripts/generate_device_keys.py")
        sys.exit(1)

    pub_pem = pub_path.read_text(encoding="utf-8")
    priv = load_private_key(priv_path)

    with httpx.Client(timeout=10) as client:
        # enroll
        r = client.post(f"{GATEWAY}/enroll", json={"device_id": args.device_id, "public_key_pem": pub_pem})
        check(r.status_code == 200, "Device enrolled", f"Enroll failed: {r.status_code} {r.text}")
        r.raise_for_status()

        # challenge
        ch_resp = client.get(f"{GATEWAY}/challenge", params={"device_id": args.device_id})
        check(ch_resp.status_code == 200, "Challenge issued", f"Challenge failed: {ch_resp.status_code} {ch_resp.text}")
        ch_resp.raise_for_status()
        ch = ch_resp.json()
        nonce, ts = ch["nonce"], ch["ts"]

        msg = f"{args.device_id}|{nonce}|{ts}".encode("utf-8")

        # craft signature
        if args.mode == "forge":
            sig_b64 = base64.b64encode(b"not-a-real-signature").decode("utf-8")
        else:
            sig = sign(priv, msg)
            sig_b64 = base64.b64encode(sig).decode("utf-8")

        payload = {"device_id": args.device_id, "nonce": nonce, "ts": ts, "signature_b64": sig_b64}

        # auth attempt #1
        auth1 = client.post(f"{GATEWAY}/auth", json=payload)

        if args.mode == "forge":
            # Expect reject
            check(
                auth1.status_code == 401,
                "Forged signature correctly rejected",
                f"Forged signature was NOT rejected: {auth1.status_code} {auth1.text}",
            )
            print(f"AUTH #1 response: {auth1.status_code} {auth1.text}")
            return

        check(auth1.status_code == 200, "Authentication succeeded", f"Auth failed: {auth1.status_code} {auth1.text}")
        auth1.raise_for_status()
        token = auth1.json()["token"]
        print(f"AUTH #1 response: {auth1.status_code} token issued")

        # telemetry without token (fail)
        tel_no = client.post(
            f"{GATEWAY}/telemetry",
            json={"data": {"temp": 22.1, "ts": datetime.now(timezone.utc).isoformat()}},
        )
        check(
            tel_no.status_code == 401,
            "Telemetry blocked without token",
            f"Telemetry was not blocked without token: {tel_no.status_code} {tel_no.text}",
        )

        # telemetry with token (pass)
        tel_yes = client.post(
            f"{GATEWAY}/telemetry",
            json={"data": {"temp": 22.1, "ts": datetime.now(timezone.utc).isoformat()}},
            headers={"Authorization": f"Bearer {token}"},
        )
        check(
            tel_yes.status_code == 200,
            "Telemetry accepted with valid token",
            f"Telemetry failed with token: {tel_yes.status_code} {tel_yes.text}",
        )

        # replay attempt (reuse same auth payload)
        if args.mode == "replay":
            auth2 = client.post(f"{GATEWAY}/auth", json=payload)
            check(
                auth2.status_code == 401,
                "Replay correctly rejected (nonce already used)",
                f"Replay was NOT rejected: {auth2.status_code} {auth2.text}",
            )
            print(f"AUTH #2 (replay) response: {auth2.status_code} {auth2.text}")


if __name__ == "__main__":
    main()