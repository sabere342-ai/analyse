from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from sqlalchemy import JSON, ForeignKey, LargeBinary, String, Text, create_engine, event, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker


def private_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.chmod(0o700)
    return path


def data_dir() -> Path:
    default = "/tmp/madrid-runtime" if os.environ.get("MADRID_DATABASE_URL") else "data"
    return private_dir(Path(os.environ.get("MADRID_DATA_DIR", default)).resolve())


class Base(DeclarativeBase):
    pass


class Batch(Base):
    __tablename__ = "batches"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    identity: Mapped[str] = mapped_column(String, unique=True)
    filename: Mapped[str] = mapped_column(String)
    checksum: Mapped[str] = mapped_column(String)
    report_type: Mapped[str] = mapped_column(String)
    scope: Mapped[str] = mapped_column(String)
    start: Mapped[str] = mapped_column(String)
    end: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="staged")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    rows: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    issues: Mapped[list[str]] = mapped_column(JSON)
    reconciliation: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[str] = mapped_column(String)


class Audit(Base):
    __tablename__ = "audit"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    batch_id: Mapped[str | None] = mapped_column(ForeignKey("batches.id"), nullable=True)
    action: Mapped[str] = mapped_column(String)
    reason: Mapped[str] = mapped_column(Text, default="")
    at: Mapped[str] = mapped_column(String)


class Owner(Base):
    __tablename__ = "owner"
    id: Mapped[int] = mapped_column(primary_key=True)
    password_hash: Mapped[str] = mapped_column(String)


class LoginSession(Base):
    __tablename__ = "sessions"
    token_hash: Mapped[str] = mapped_column(String, primary_key=True)
    expires: Mapped[int]


class Setting(Base):
    __tablename__ = "settings"
    id: Mapped[int] = mapped_column(primary_key=True)
    values: Mapped[dict[str, Any]] = mapped_column(JSON)


class Original(Base):
    __tablename__ = "originals"
    name: Mapped[str] = mapped_column(String, primary_key=True)
    content: Mapped[bytes] = mapped_column(LargeBinary)


class AuthThrottle(Base):
    __tablename__ = "auth_throttle"
    id: Mapped[int] = mapped_column(primary_key=True)
    attempts: Mapped[list[float]] = mapped_column(JSON)


def make_engine(path: Path, database_url: str | None = None) -> Engine:
    if database_url:
        url = make_url(database_url)
        if url.get_backend_name() not in {"postgres", "postgresql"}:
            raise ValueError("cloud_database_must_be_postgresql")
        url = url.set(drivername="postgresql+psycopg")
        return create_engine(
            url,
            hide_parameters=True,
            pool_pre_ping=True,
            pool_size=2,
            max_overflow=2,
            connect_args={
                "sslmode": "verify-full",
                "sslrootcert": os.environ.get(
                    "MADRID_DATABASE_CA_FILE", "/etc/ssl/certs/ca-certificates.crt"
                ),
                "connect_timeout": 15,
            },
        )
    engine = create_engine(
        f"sqlite:///{path}", connect_args={"check_same_thread": False, "timeout": 30}, hide_parameters=True
    )

    @event.listens_for(engine, "connect")
    def configure(connection: Any, _: Any) -> None:
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=30000")

    return engine


def session_factory(engine: Engine) -> sessionmaker:
    return sessionmaker(engine, expire_on_commit=False)


def lock_writes(session: Session) -> None:
    """Serialize shared-store decisions across local processes or cloud instances."""
    if session.get_bind().dialect.name == "postgresql":
        session.execute(text("SELECT pg_advisory_xact_lock(74930217)"))
    else:
        session.execute(text("BEGIN IMMEDIATE"))
