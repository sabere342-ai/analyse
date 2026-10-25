from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import time
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from madrid.db import LoginSession, Owner


def hash_password(password: str, salt: bytes | None = None) -> str:
    if len(password) < 12 or len(password) > 256:
        raise ValueError("password_length_12_to_256")
    salt = salt or os.urandom(16)
    value = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return salt.hex() + "$" + value.hex()


def verify_password(password: str, stored: str) -> bool:
    try:
        return hmac.compare_digest(hash_password(password, bytes.fromhex(stored.split("$")[0])), stored)
    except ValueError:
        return False


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def logged_in(session: Session, token: str | None) -> bool:
    if not token:
        return False
    found = session.get(LoginSession, token_hash(token))
    return bool(found and found.expires > int(time.time()))


def login(session: Session, password: str, *, commit: bool = True) -> str | None:
    owner = session.scalar(select(Owner))
    if not owner or not verify_password(password, owner.password_hash):
        return None
    session.execute(delete(LoginSession).where(LoginSession.expires < int(time.time())))
    token = secrets.token_urlsafe(32)
    session.add(LoginSession(token_hash=token_hash(token), expires=int(time.time()) + 12 * 3600))
    if commit:
        session.commit()
    return token


def redact_batch(batch: Any, include_rows: bool = True) -> dict[str, Any]:
    result = {
        "id": batch.id,
        "filename": batch.filename,
        "checksum": batch.checksum,
        "report_type": batch.report_type,
        "scope": batch.scope,
        "start": batch.start,
        "end": batch.end,
        "status": batch.status,
        "metadata": batch.metadata_json,
        "issues": batch.issues,
        "reconciliation": batch.reconciliation,
        "created_at": batch.created_at,
    }
    if include_rows:
        result["rows"] = batch.rows
    return result
