"""Force-resync the admin user password from ADMIN_EMAIL/ADMIN_PASSWORD in .env.

Usage:
    python reset_admin.py

This is usually NOT needed because server.py startup already resyncs on every
boot. Provided as a rescue tool in case the server hasn't been started yet
and you want to pre-seed or reset a stale DB.
"""
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
import bcrypt

HERE = Path(__file__).parent.resolve()
load_dotenv(HERE / ".env")

ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@profund.ai").lower()
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "ProFund2026!")
DB_PATH = HERE / "profund.db"


def hash_pw(pw: str) -> str:
    return bcrypt.hashpw(pw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def main():
    if not DB_PATH.exists():
        print(f"No DB at {DB_PATH} — will be created by backend on first start.")
        print(f"Admin will be seeded then as: {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
        return

    con = sqlite3.connect(str(DB_PATH))
    cur = con.cursor()
    try:
        cur.execute("SELECT id FROM users WHERE email = ?", (ADMIN_EMAIL,))
        row = cur.fetchone()
        h = hash_pw(ADMIN_PASSWORD)
        if row:
            cur.execute("UPDATE users SET password_hash = ? WHERE email = ?", (h, ADMIN_EMAIL))
            print(f"Admin password RESET for: {ADMIN_EMAIL}")
        else:
            cur.execute(
                "INSERT INTO users (id, email, password_hash, name, role, created_at) "
                "VALUES (?, ?, ?, 'Admin', 'admin', ?)",
                (str(uuid.uuid4()), ADMIN_EMAIL, h, datetime.now(timezone.utc).isoformat()),
            )
            print(f"Admin user CREATED: {ADMIN_EMAIL}")
        con.commit()
        print(f"\nLogin with:\n  Email:    {ADMIN_EMAIL}\n  Password: {ADMIN_PASSWORD}")
    except sqlite3.OperationalError as e:
        print(f"ERROR: {e}\nDB may not be initialized yet. Start the backend once first.")
    finally:
        con.close()


if __name__ == "__main__":
    main()
