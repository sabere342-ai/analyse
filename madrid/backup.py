"""Consistent, encrypted backup and safe restore into a NEW directory only."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import sqlite3
import tempfile
import zipfile
from contextlib import closing
from getpass import getpass
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import select
from sqlalchemy.engine import Engine

from madrid.db import Base, Original, make_engine, private_dir

MAGIC = b"MADRID_BACKUP_1\n"


def key_for(password: str, salt: bytes) -> bytes:
    if len(password) < 12:
        raise ValueError("backup_passphrase_minimum_12_characters")
    return hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)


def create_backup(directory: Path, password: str) -> bytes:
    db = directory / "madrid.sqlite3"
    if not db.exists():
        raise ValueError("database_missing")
    # VACUUM INTO uses a consistent snapshot, without copying an active WAL database.
    snapshot = directory / ("backup-" + os.urandom(8).hex() + ".sqlite3")
    try:
        with closing(sqlite3.connect(db)) as connection, connection:
            connection.execute("VACUUM INTO ?", (str(snapshot),))
        buffer = io.BytesIO()
        hashes = {}
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            entries = [(snapshot, "madrid.sqlite3")]
            with closing(sqlite3.connect(snapshot)) as captured:
                sources = captured.execute("SELECT checksum, filename, status FROM batches").fetchall()
            seen = set()
            for checksum, filename, status in sources:
                original = directory / "originals" / (checksum + Path(filename).suffix.lower())
                if not original.exists():
                    if status in {"staged", "accepted"}:
                        raise ValueError("backup_required_original_missing")
                    continue
                if hashlib.sha256(original.read_bytes()).hexdigest() != checksum:
                    raise ValueError("backup_source_integrity_failure")
                if original.name not in seen:
                    entries.append((original, "originals/" + original.name))
                    seen.add(original.name)
            for file, name in entries:
                content = file.read_bytes()
                hashes[name] = hashlib.sha256(content).hexdigest()
                archive.writestr(name, content)
            archive.writestr("manifest.json", json.dumps({"format": 1, "sha256": hashes}, sort_keys=True))
        salt, nonce = os.urandom(16), os.urandom(12)
        return MAGIC + salt + nonce + AESGCM(key_for(password, salt)).encrypt(nonce, buffer.getvalue(), MAGIC)
    finally:
        snapshot.unlink(missing_ok=True)


def restore_backup(content: bytes, destination: Path, password: str) -> dict[str, str]:
    if destination.exists():
        raise ValueError("restore_requires_new_destination")
    if not content.startswith(MAGIC):
        raise ValueError("invalid_backup_format")
    offset = len(MAGIC)
    salt, nonce = content[offset : offset + 16], content[offset + 16 : offset + 28]
    decrypted = AESGCM(key_for(password, salt)).decrypt(nonce, content[offset + 28 :], MAGIC)
    with zipfile.ZipFile(io.BytesIO(decrypted)) as archive:
        if sum(i.file_size for i in archive.infolist()) > 1024**3:
            raise ValueError("backup_expansion_limit")
        manifest = json.loads(archive.read("manifest.json"))["sha256"]
        for name, expected in manifest.items():
            if name != "madrid.sqlite3" and not (
                name.startswith("originals/") and len(Path(name).parts) == 2
            ):
                raise ValueError("unsafe_backup_path")
            if Path(name).is_absolute() or ".." in Path(name).parts:
                raise ValueError("unsafe_backup_path")
            if hashlib.sha256(archive.read(name)).hexdigest() != expected:
                raise ValueError("backup_checksum_mismatch")
        if "madrid.sqlite3" not in manifest:
            raise ValueError("backup_database_missing")
        private_dir(destination)
        for name in manifest:
            target = destination / name
            private_dir(target.parent)
            target.write_bytes(archive.read(name))
            target.chmod(0o600)
    with closing(sqlite3.connect(destination / "madrid.sqlite3")) as connection, connection:
        if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("restored_database_integrity_failure")
        connection.execute("DELETE FROM sessions")
    return manifest


def create_cloud_backup(engine: Engine, password: str) -> bytes:
    """One consistent PostgreSQL snapshot, restorable by the existing encrypted local format."""
    from madrid.app import migrate

    if engine.dialect.name != "postgresql":
        raise ValueError("cloud_backup_requires_postgresql")
    with tempfile.TemporaryDirectory(prefix="madrid-backup-") as temporary:
        directory = private_dir(Path(temporary))
        target = make_engine(directory / "madrid.sqlite3")
        migrate(target)
        try:
            with engine.connect().execution_options(isolation_level="REPEATABLE READ") as source:
                with source.begin(), target.begin() as destination:
                    for table in Base.metadata.sorted_tables:
                        records = [dict(row) for row in source.execute(select(table)).mappings()]
                        if records:
                            destination.execute(table.insert(), records)
                    for name, content in source.execute(select(Original.name, Original.content)):
                        if (
                            len(name) < 68
                            or any(c not in "0123456789abcdef" for c in name[:64])
                            or name[64:] not in {".pdf", ".csv", ".xls", ".xlsx"}
                        ):
                            raise ValueError("unsafe_original_name")
                        file = private_dir(directory / "originals") / name
                        file.write_bytes(content)
                        file.chmod(0o600)
            return create_backup(directory, password)
        finally:
            target.dispose()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["create", "restore"])
    parser.add_argument("file", type=Path)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument(
        "--cloud",
        action="store_true",
        help="Create from MADRID_DATABASE_URL; restore remains local and never overwrites a store",
    )
    args = parser.parse_args()
    if args.cloud and (args.action != "create" or not os.environ.get("MADRID_DATABASE_URL")):
        raise ValueError("cloud_create_requires_database_url")
    password = getpass("Backup passphrase (12+ characters): ")
    if args.action == "create":
        if args.file.exists():
            raise ValueError("refusing_to_overwrite_backup")
        args.file.parent.mkdir(parents=True, exist_ok=True)
        with args.file.open("xb") as output:
            args.file.chmod(0o600)
            if args.cloud:
                engine = make_engine(args.directory / "unused.sqlite3", os.environ["MADRID_DATABASE_URL"])
                try:
                    output.write(create_cloud_backup(engine, password))
                finally:
                    engine.dispose()
            else:
                output.write(create_backup(args.directory.resolve(), password))
        print("Encrypted backup created.")
    else:
        manifest = restore_backup(args.file.read_bytes(), args.directory.resolve(), password)
        print(f"Restored and verified {len(manifest)} files. Sessions invalidated.")


if __name__ == "__main__":
    main()
