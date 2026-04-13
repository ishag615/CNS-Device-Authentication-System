#!/usr/bin/env python3
import argparse, time, base64, statistics
from pathlib import Path

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


def p95(values):
    if not values:
        return None
    vals = sorted(values)
    idx = int(0.95 * (len(vals) - 1))
    return vals[idx]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=50, help="number of auth attempts")
    ap.add_argument("--device-id", default="test_device")
    ap.add_argument("--public-key", default="keys/device_public.pem")
    ap.add_argument("--private-key", default="keys/device_private.pem")
    args = ap.parse_args()

    pub_pem = Path(args.public_key).read_text(encoding="utf-8")
    priv = load_private_key(Path(args.private_key))

    times_ms = []
    failures = 0

    with httpx.Client(timeout=10) as client:
        # ensure device enrolled once
        r = client.post(f"{GATEWAY}/enroll", json={"device_id": args.device_id, "public_key_pem": pub_pem})
        r.raise_for_status()

        for i in range(args.n):
            # challenge
            ch = client.get(f"{GATEWAY}/challenge", params={"device_id": args.device_id})
            if ch.status_code != 200:
                failures += 1
                continue
            chj = ch.json()
            nonce, ts = chj["nonce"], chj["ts"]

            msg = f"{args.device_id}|{nonce}|{ts}".encode("utf-8")
            sig_b64 = base64.b64encode(sign(priv, msg)).decode("utf-8")

            payload = {"device_id": args.device_id, "nonce": nonce, "ts": ts, "signature_b64": sig_b64}

            # time the /auth request
            t0 = time.perf_counter()
            auth = client.post(f"{GATEWAY}/auth", json=payload)
            t1 = time.perf_counter()

            if auth.status_code == 200:
                times_ms.append((t1 - t0) * 1000.0)
            else:
                failures += 1

    if times_ms:
        avg = statistics.mean(times_ms)
        p95v = p95(times_ms)
        print(f"Auth attempts: {args.n}")
        print(f"Success: {len(times_ms)}  Failures: {failures}")
        print(f"Avg /auth latency: {avg:.2f} ms")
        print(f"P95 /auth latency: {p95v:.2f} ms")
    else:
        print("No successful auth attempts. Is the gateway running?")


if __name__ == "__main__":
    main()