import argparse, sqlite3
from pathlib import Path

DB_PATH = Path("data/iot_auth.db")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--device-id", required=True)
    ap.add_argument("--public-key-pem", required=True, help="Path to PEM public key file")
    args = ap.parse_args()

    pem = Path(args.public_key_pem).read_text(encoding="utf-8")

    con = sqlite3.connect(DB_PATH)
    try:
        con.execute(
            "INSERT OR REPLACE INTO devices(device_id, public_key_pem) VALUES (?, ?)",
            (args.device_id, pem),
        )
        con.commit()
        print(f"Enrolled device: {args.device_id}")
    finally:
        con.close()

if __name__ == "__main__":
    main()