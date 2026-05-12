"""Shared dependencies for V11 modular routers.

Mirrors the auth/db helpers already used by server.py, but kept here so
the new V11 routers/services can be imported without circular imports.
"""
import os
import aiosqlite
import jwt
from datetime import datetime, timezone
from fastapi import HTTPException, Request

from database import DB_PATH

JWT_SECRET = os.environ.get("JWT_SECRET", "fallback-secret-key")
JWT_ALGORITHM = "HS256"
EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")


async def get_db():
    db = await aiosqlite.connect(str(DB_PATH))
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA foreign_keys=ON")
    return db


async def get_current_user(request: Request) -> dict:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = auth_header[7:]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        db = await get_db()
        cursor = await db.execute(
            "SELECT id, email, name, role FROM users WHERE id = ?",
            (payload["sub"],),
        )
        row = await cursor.fetchone()
        await db.close()
        if not row:
            raise HTTPException(status_code=401, detail="User not found")
        return dict(row)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
