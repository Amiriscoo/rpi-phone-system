from datetime import datetime, timedelta, timezone
from hashlib import scrypt
from hmac import compare_digest
import base64, os, secrets, time
from typing import Annotated
import jwt
from fastapi import Depends, FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from .database import connection, init_db

SECRET = os.environ.get("RPI_PHONE_JWT_SECRET")
if not SECRET:
    raise RuntimeError("Set RPI_PHONE_JWT_SECRET before starting the server")
app = FastAPI(title="Raspberry Pi Phone Server", version="1.0")
init_db()
active_sockets: dict[int, set[WebSocket]] = {}
request_times: dict[str, list[float]] = {}

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    return base64.urlsafe_b64encode(salt + scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)).decode()

def verify_password(password: str, encoded: str) -> bool:
    raw = base64.urlsafe_b64decode(encoded.encode())
    return compare_digest(scrypt(password.encode(), salt=raw[:16], n=2**14, r=8, p=1), raw[16:])

def token_for(user_id: int) -> str:
    payload = {"sub": str(user_id), "exp": datetime.now(timezone.utc) + timedelta(hours=12)}
    return jwt.encode(payload, SECRET, algorithm="HS256")

def current_user(authorization: Annotated[str | None, Header()] = None) -> int:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Authentication required")
    try:
        return int(jwt.decode(authorization[7:], SECRET, algorithms=["HS256"])["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError) as exc:
        raise HTTPException(401, "Invalid or expired session") from exc

def rate_limit(key: str, limit: int = 60):
    now = time.monotonic()
    recent = [stamp for stamp in request_times.get(key, []) if now - stamp < 60]
    if len(recent) >= limit:
        raise HTTPException(429, "Too many requests")
    request_times[key] = recent + [now]

class Credentials(BaseModel):
    username: str = Field(min_length=3, max_length=32, pattern=r"^[a-zA-Z0-9_.-]+$")
    password: str = Field(min_length=8, max_length=128)
class DeviceRegistration(BaseModel):
    name: str = Field(min_length=1, max_length=80)
class MessageIn(BaseModel):
    body: str = Field(min_length=1, max_length=4000)
class ContactIn(BaseModel):
    display_name: str = Field(min_length=1, max_length=80)
    username: str | None = None
    phone: str | None = None

@app.get("/health")
def health():
    return {"ok": True, "service": "rpi-phone", "time": datetime.now(timezone.utc).isoformat()}

@app.post("/auth/register")
def register(credentials: Credentials):
    with connection() as db:
        try:
            cursor = db.execute("INSERT INTO users(username, password_hash) VALUES (?, ?)", (credentials.username, hash_password(credentials.password)))
        except Exception as exc:
            raise HTTPException(409, "Username is already registered") from exc
    return {"token": token_for(cursor.lastrowid), "user_id": cursor.lastrowid, "username": credentials.username}

@app.post("/auth/login")
def login(credentials: Credentials):
    rate_limit(credentials.username, 10)
    with connection() as db:
        user = db.execute("SELECT * FROM users WHERE username = ?", (credentials.username,)).fetchone()
    if not user or not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(401, "Incorrect username or password")
    return {"token": token_for(user["id"]), "user_id": user["id"], "username": user["username"]}

@app.post("/devices")
def register_device(data: DeviceRegistration, user_id: int = Depends(current_user)):
    device_key = secrets.token_urlsafe(32)
    with connection() as db:
        db.execute("INSERT INTO devices(user_id, name, device_key, last_seen) VALUES (?, ?, ?, CURRENT_TIMESTAMP)", (user_id, data.name, device_key))
    return {"name": data.name, "device_key": device_key}

@app.get("/me")
def me(user_id: int = Depends(current_user)):
    with connection() as db:
        user = db.execute("SELECT id, username, created_at FROM users WHERE id = ?", (user_id,)).fetchone()
        contacts = db.execute("SELECT id, display_name, username, phone FROM contacts WHERE owner_id = ?", (user_id,)).fetchall()
    return {"user": dict(user), "contacts": [dict(contact) for contact in contacts]}

@app.post("/contacts")
def add_contact(data: ContactIn, user_id: int = Depends(current_user)):
    with connection() as db:
        cursor = db.execute("INSERT INTO contacts(owner_id, display_name, username, phone) VALUES (?, ?, ?, ?)", (user_id, data.display_name, data.username, data.phone))
    return {"id": cursor.lastrowid, **data.model_dump()}

@app.get("/users")
def users(user_id: int = Depends(current_user)):
    with connection() as db:
        rows = db.execute("SELECT id, username FROM users WHERE id != ? ORDER BY username", (user_id,)).fetchall()
    return [dict(row) for row in rows]

@app.get("/messages/{other_user_id}")
def messages(other_user_id: int, user_id: int = Depends(current_user)):
    with connection() as db:
        rows = db.execute("SELECT id, sender_id, recipient_id, body, created_at FROM messages WHERE (sender_id = ? AND recipient_id = ?) OR (sender_id = ? AND recipient_id = ?) ORDER BY id", (user_id, other_user_id, other_user_id, user_id)).fetchall()
        db.execute("UPDATE messages SET delivered = 1 WHERE sender_id = ? AND recipient_id = ?", (other_user_id, user_id))
    return [dict(row) for row in rows]

async def notify(user_id: int, message: dict):
    for socket in list(active_sockets.get(user_id, set())):
        try:
            await socket.send_json(message)
        except Exception:
            active_sockets[user_id].discard(socket)

@app.post("/messages/{recipient_id}")
async def send_message(recipient_id: int, data: MessageIn, user_id: int = Depends(current_user)):
    with connection() as db:
        if not db.execute("SELECT id FROM users WHERE id = ?", (recipient_id,)).fetchone():
            raise HTTPException(404, "Recipient not found")
        cursor = db.execute("INSERT INTO messages(sender_id, recipient_id, body) VALUES (?, ?, ?)", (user_id, recipient_id, data.body.strip()))
        row = db.execute("SELECT id, sender_id, recipient_id, body, created_at FROM messages WHERE id = ?", (cursor.lastrowid,)).fetchone()
    payload = dict(row)
    await notify(recipient_id, payload)
    return payload

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str):
    try:
        user_id = int(jwt.decode(token, SECRET, algorithms=["HS256"])["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        await websocket.close(code=4001)
        return
    await websocket.accept()
    active_sockets.setdefault(user_id, set()).add(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        active_sockets[user_id].discard(websocket)
