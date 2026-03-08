import sqlite3
from pathlib import Path

DB_PATH = Path("data/iot_auth.db")

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS devices (
  device_id TEXT PRIMARY KEY,
  public_key_pem TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- replay prevention foundation
CREATE TABLE IF NOT EXISTS nonces (
    device_id TEXT NOT NULL,
    nonce TEXT NOT NULL,
    issued_at TEXT NOT NULL DEFAULT (datetime('now')),
    used INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (device_id, nonce),
    FOREIGN KEY (device_id) REFERENCES devices(device_id) ON DELETE CASCADE
);
"""

def main():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    try:
        con.executescript(SCHEMA)
        con.commit()
        print(f"Database initialized at: {DB_PATH}")
    finally:
        con.close()

if __name__ == "__main__":
    main()