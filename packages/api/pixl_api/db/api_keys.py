"""API key database operations."""

from __future__ import annotations

import hashlib
import json
import secrets
import uuid

from pixl_api.db._connection import get_connection


def create_api_key(
    user_id: str,
    name: str,
    scopes: list[str] | None = None,
    rate_limit_rpm: int = 60,
) -> dict:
    """Create an API key. Returns the raw key only once.

    The raw key is ``pk_`` + 32 random hex chars.
    Only the SHA-256 hash is stored in the database.
    """
    if scopes is None:
        scopes = []
    key_id = uuid.uuid4().hex
    raw_key = "pk_" + secrets.token_hex(16)
    prefix = raw_key[:11]  # "pk_" + 8 hex chars
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    conn = get_connection()
    conn.execute(
        "INSERT INTO api_keys "
        "(id, user_id, name, key_hash, prefix, scopes_json, rate_limit_rpm) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (key_id, user_id, name, key_hash, prefix, json.dumps(scopes), rate_limit_rpm),
    )
    conn.commit()
    conn.close()
    return {
        "id": key_id,
        "key": raw_key,
        "name": name,
        "prefix": prefix,
        "scopes": scopes,
        "rate_limit_rpm": rate_limit_rpm,
    }


def list_api_keys(user_id: str) -> list[dict]:
    """List active API keys for a user (without key hashes)."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, name, prefix, scopes_json, rate_limit_rpm, is_active, created_at "
        "FROM api_keys WHERE user_id = ? AND is_active = 1 ORDER BY created_at",
        (user_id,),
    ).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["scopes"] = json.loads(d.pop("scopes_json"))
        d["is_active"] = bool(d["is_active"])
        result.append(d)
    return result


def revoke_api_key(key_id: str, user_id: str) -> bool:
    """Revoke (soft-delete) an API key. Only the owning user can revoke."""
    conn = get_connection()
    cursor = conn.execute(
        "UPDATE api_keys SET is_active = 0 WHERE id = ? AND user_id = ? AND is_active = 1",
        (key_id, user_id),
    )
    conn.commit()
    conn.close()
    return cursor.rowcount > 0
