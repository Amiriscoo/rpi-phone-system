from pathlib import Path
import sqlite3

DB_PATH = Path(__file__).resolve().parents[1] / "database" / "phone.db"


def connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def init_db():
    with connection() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS devices (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE, name TEXT NOT NULL, device_key TEXT UNIQUE NOT NULL, last_seen TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS contacts (id INTEGER PRIMARY KEY AUTOINCREMENT, owner_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE, display_name TEXT NOT NULL, username TEXT, phone TEXT);
            CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, sender_id INTEGER NOT NULL REFERENCES users(id), recipient_id INTEGER NOT NULL REFERENCES users(id), body TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, delivered INTEGER NOT NULL DEFAULT 0);
            CREATE INDEX IF NOT EXISTS messages_pair ON messages(sender_id, recipient_id, id);
            """
        )
