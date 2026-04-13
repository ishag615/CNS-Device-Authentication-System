from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
import base64, secrets, sqlite3
from pathlib import Path
from datetime import datetime, timezone, timedelta

from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding

DB_PATH = Path("data/iot_auth.db")
FRESHNESS_SECONDS = 30
TOKEN_TTL_SECONDS = 60

app = FastAPI()

class EnrollReq(BaseModel):
    device_id: str
    public_key_pem: str

class AuthReq(BaseModel):
    device_id: str
    nonce: str
    ts: str
    signature_b64: str

class TelemetryReq(BaseModel):
    data: dict

def db():
    if not DB_PATH.exists():
        raise HTTPException(500, "DB missing. Run: python3 scripts/setup_database.py")
    return sqlite3.connect(DB_PATH)

def get_public_key(device_id: str):
    con = db()
    try:
        row = con.execute("SELECT public_key_pem FROM devices WHERE device_id=?", (device_id,)).fetchone()
    finally:
        con.close()
    if not row:
        raise HTTPException(401, "Unknown device_id")
    return serialization.load_pem_public_key(row[0].encode("utf-8"))

def check_freshness(ts_iso: str):
    try:
        ts = datetime.fromisoformat(ts_iso.replace("Z", "+00:00"))
    except Exception:
        raise HTTPException(400, "Bad ts format")
    now = datetime.now(timezone.utc)
    if abs((now - ts).total_seconds()) > FRESHNESS_SECONDS:
        raise HTTPException(401, "Stale timestamp")

def check_nonce(device_id: str, nonce: str):
    con = db()
    try:
        row = con.execute("SELECT used FROM nonces WHERE device_id=? AND nonce=?", (device_id, nonce)).fetchone()
    finally:
        con.close()
    if not row:
        raise HTTPException(401, "Unknown nonce (request a new challenge)")
    if row[0] == 1:
        raise HTTPException(401, "Replay detected (nonce already used)")

def mark_nonce_used(device_id: str, nonce: str):
    con = db()
    try:
        con.execute("UPDATE nonces SET used=1 WHERE device_id=? AND nonce=?", (device_id, nonce))
        con.commit()
    finally:
        con.close()

def verify_sig(public_key, message: bytes, signature: bytes):
    try:
        public_key.verify(
            signature,
            message,
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
            hashes.SHA256(),
        )
    except Exception:
        raise HTTPException(401, "Invalid signature")

def issue_token(device_id: str):
    token = secrets.token_urlsafe(24)
    expires_at = (datetime.now(timezone.utc) + timedelta(seconds=TOKEN_TTL_SECONDS)).isoformat()
    con = db()
    try:
        con.execute("INSERT INTO tokens(token, device_id, expires_at) VALUES (?, ?, ?)", (token, device_id, expires_at))
        con.commit()
    finally:
        con.close()
    return token, expires_at

def verify_token(auth_header: str | None) -> str:
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(401, "Missing Bearer token")
    token = auth_header.split(" ", 1)[1].strip()

    con = db()
    try:
        row = con.execute("SELECT device_id, expires_at FROM tokens WHERE token=?", (token,)).fetchone()
    finally:
        con.close()

    if not row:
        raise HTTPException(401, "Invalid token")

    device_id, expires_at = row
    exp = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
    if datetime.now(timezone.utc) > exp:
        raise HTTPException(401, "Expired token")

    return device_id

@app.post("/enroll")
def enroll(req: EnrollReq):
    con = db()
    try:
        con.execute("INSERT OR REPLACE INTO devices(device_id, public_key_pem) VALUES (?, ?)",
                    (req.device_id, req.public_key_pem))
        con.commit()
    finally:
        con.close()
    return {"status": "ok", "device_id": req.device_id}

@app.get("/challenge")
def challenge(device_id: str):
    _ = get_public_key(device_id)  # ensure enrolled
    nonce = secrets.token_hex(16)
    ts = datetime.now(timezone.utc).isoformat()

    con = db()
    try:
        con.execute("INSERT OR REPLACE INTO nonces(device_id, nonce, used) VALUES (?, ?, 0)", (device_id, nonce))
        con.commit()
    finally:
        con.close()

    return {"device_id": device_id, "nonce": nonce, "ts": ts}

@app.post("/auth")
def auth(req: AuthReq):
    check_freshness(req.ts)
    check_nonce(req.device_id, req.nonce)

    public_key = get_public_key(req.device_id)
    message = f"{req.device_id}|{req.nonce}|{req.ts}".encode("utf-8")
    signature = base64.b64decode(req.signature_b64)

    verify_sig(public_key, message, signature)
    mark_nonce_used(req.device_id, req.nonce)

    token, expires_at = issue_token(req.device_id)
    return {"token": token, "expires_at": expires_at}

@app.post("/telemetry")
def telemetry(req: TelemetryReq, authorization: str | None = Header(default=None)):
    device_id = verify_token(authorization)
    return {"status": "accepted", "device_id": device_id, "received": req.data}