from __future__ import annotations

import csv
import hashlib
import hmac
import io
import json
import os
import re
import subprocess
import time
from contextlib import asynccontextmanager
from datetime import date, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from alembic import command
from alembic.config import Config
from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import delete, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from madrid.analytics import amount, calculate
from madrid.auth import hash_password, logged_in, login, redact_batch, token_hash
from madrid.contracts import ImportSpec, Rules, decimal_value
from madrid.db import (
    Audit,
    AuthThrottle,
    Batch,
    LoginSession,
    Original,
    Owner,
    Setting,
    data_dir,
    lock_writes,
    make_engine,
    private_dir,
    session_factory,
)
from madrid.extraction import MAX_BYTES
from madrid.ingestion import compare_batch, now, stage, transition
from madrid.reporting import export_report

ROOT = Path(__file__).resolve().parent.parent


class BodyLimitMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        consumed = 0

        async def limited_receive() -> Message:
            nonlocal consumed
            message = await receive()
            if message["type"] == "http.request":
                consumed += len(message.get("body", b""))
                if consumed > MAX_BYTES + 65536:
                    raise HTTPException(413, "upload_too_large")
            return message

        await self.app(scope, limited_receive, send)


class Password(BaseModel):
    model_config = ConfigDict(extra="forbid")
    password: str = Field(min_length=12, max_length=256)


class Action(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: str = Field(pattern="^(accept|reject|rollback)$")
    reason: str = Field(default="", max_length=1000)


class Reason(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str = Field(min_length=1, max_length=1000)


def migrate(engine: Any) -> None:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "migrations"))
    with engine.begin() as connection:
        if engine.dialect.name == "postgresql":
            connection.execute(text("SELECT pg_advisory_xact_lock(74930217)"))
        config.attributes["connection"] = connection
        command.upgrade(config, "head")


def create_app(directory: Path | None = None) -> FastAPI:
    database_url = os.environ.get("MADRID_DATABASE_URL") if directory is None else None
    if directory is None and os.environ.get("MADRID_REQUIRE_CLOUD_DATABASE") == "1" and not database_url:
        raise RuntimeError("durable_cloud_database_required")
    directory = private_dir(directory or data_dir())
    engine = make_engine(directory / "madrid.sqlite3", database_url)
    factory = session_factory(engine)

    @asynccontextmanager
    async def lifespan(_: FastAPI):  # type: ignore[no-untyped-def]
        migrate(engine)
        if engine.dialect.name == "sqlite":
            (directory / "madrid.sqlite3").chmod(0o600)
        yield
        engine.dispose()

    app = FastAPI(title="Madrid Retail Intelligence", lifespan=lifespan, docs_url=None, redoc_url=None)
    app.state.factory = factory
    app.state.directory = directory
    app.add_middleware(BodyLimitMiddleware)
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=os.environ.get("MADRID_ALLOWED_HOSTS", "localhost,127.0.0.1,testserver").split(","),
    )

    @app.middleware("http")
    async def security(request: Request, call_next: Any) -> Response:
        if request.method not in {"GET", "HEAD", "OPTIONS"} and request.url.path.startswith("/api/"):
            if request.headers.get("X-Requested-With") != "Madrid":
                return Response(
                    '{"detail":"csrf_header_required"}', status_code=403, media_type="application/json"
                )
            origin = request.headers.get("origin")
            allowed = {
                str(request.base_url).rstrip("/"),
                "http://localhost:5173",
                "http://127.0.0.1:5173",
                "http://127.0.0.1:4173",
            }
            configured = os.environ.get("MADRID_ORIGIN")
            if configured:
                allowed.add(configured.rstrip("/"))
            for key in ("VERCEL_URL", "VERCEL_BRANCH_URL"):
                hostname = os.environ.get(key, "")
                if re.fullmatch(r"[a-z0-9-]+\.vercel\.app", hostname):
                    allowed.add("https://" + hostname)
            if origin and origin.rstrip("/") not in allowed:
                return Response(
                    '{"detail":"origin_not_allowed"}', status_code=403, media_type="application/json"
                )
            length = request.headers.get("content-length")
            if length and (not length.isdigit() or int(length) > MAX_BYTES + 65536):
                return Response(
                    '{"detail":"upload_too_large"}', status_code=413, media_type="application/json"
                )
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'self'"
        )
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    def session() -> Any:
        with factory() as db:
            yield db

    def authenticated(request: Request, db: Session = Depends(session)) -> None:
        if not logged_in(db, request.cookies.get("madrid_session")):
            raise HTTPException(401, "authentication_required")

    protected = [Depends(authenticated)]

    @app.get("/api/templates/{report_type}", dependencies=protected)
    def template(report_type: str) -> Response:
        templates = {
            "snapshot": [
                ["barcode", "name", "category", "quantity", "reserved", "available", "introduced"],
                ["000366", "منتج تجريبي — ليس بيانات محل", "تجريبي", "10", "2", "8", "01/10/2026"],
                ["TOTAL", "", "", "10", "2", "8", ""],
            ],
            "sales": [
                [
                    "barcode",
                    "name",
                    "category",
                    "rep",
                    "sold",
                    "returned",
                    "gross",
                    "discount",
                    "return_value",
                    "net",
                    "cogs",
                ],
                ["000366", "منتج تجريبي", "تجريبي", "مندوب تجريبي", "2", "0", "200", "20", "0", "180", "100"],
                ["TOTAL", "", "", "", "2", "0", "200", "20", "0", "180", "100"],
            ],
            "movement": [
                ["barcode", "name", "date", "kind", "incoming", "outgoing", "reference"],
                ["000366", "منتج تجريبي", "01/10/2026", "purchase", "10", "0", "DEMO-1"],
                ["TOTAL", "", "", "", "10", "0", ""],
            ],
            "costs": [["barcode", "cost"], ["000366", "50"], ["TOTAL", "50"]],
            "expenses": [
                ["date", "category", "amount", "reference"],
                ["01/10/2026", "مصروف تجريبي", "25", "DEMO"],
                ["", "TOTAL", "25", ""],
            ],
            "targets": [["rep", "target"], ["مندوب تجريبي", "500"], ["TOTAL", "500"]],
        }
        if report_type not in templates:
            raise HTTPException(404, "unsupported_template")
        stream = io.StringIO(newline="")
        csv.writer(stream).writerows(templates[report_type])
        return Response(
            stream.getvalue().encode("utf-8-sig"),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="synthetic-{report_type}.csv"'},
        )

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/auth/status")
    def status(request: Request, db: Session = Depends(session)) -> dict[str, bool | int]:
        return {
            "initialized": db.get(Owner, 1) is not None,
            "authenticated": logged_in(db, request.cookies.get("madrid_session")),
            "cloud": bool(database_url),
            "max_upload_bytes": MAX_BYTES,
        }

    @app.post("/api/auth/setup")
    def setup(body: Password, request: Request, db: Session = Depends(session)) -> dict[str, bool]:
        host = urlparse(str(request.url)).hostname
        if database_url:
            expected = os.environ.get("MADRID_SETUP_TOKEN_HASH", "")
            supplied = request.headers.get("X-Madrid-Setup", "")
            if (
                not expected
                or not supplied
                or not hmac.compare_digest(hashlib.sha256(supplied.encode()).hexdigest(), expected)
            ):
                raise HTTPException(403, "owner_setup_requires_invitation")
        elif (
            host not in {"localhost", "127.0.0.1", "testserver"}
            or not request.client
            or request.client.host not in {"127.0.0.1", "::1", "testclient"}
        ):
            raise HTTPException(403, "owner_setup_requires_local_access")
        if db.get(Owner, 1):
            raise HTTPException(409, "owner_already_configured")
        db.add(Owner(id=1, password_hash=hash_password(body.password)))
        db.add(Audit(action="owner_setup", reason="invitation" if database_url else "local", at=now()))
        try:
            db.commit()
        except IntegrityError as exc:
            raise HTTPException(409, "owner_already_configured") from exc
        return {"ok": True}

    @app.post("/api/auth/login")
    def sign_in(
        body: Password, request: Request, response: Response, db: Session = Depends(session)
    ) -> dict[str, bool]:
        lock_writes(db)
        throttle = db.get(AuthThrottle, 1)
        attempts = [t for t in (throttle.attempts if throttle else []) if t > time.time() - 300]
        if len(attempts) >= 10:
            raise HTTPException(429, "login_rate_limited")
        token = login(db, body.password, commit=False)
        if not token:
            attempts.append(time.time())
            if throttle:
                throttle.attempts = attempts
            else:
                db.add(AuthThrottle(id=1, attempts=attempts))
            db.commit()
            raise HTTPException(401, "invalid_credentials")
        if throttle:
            db.delete(throttle)
        db.commit()
        response.set_cookie(
            "madrid_session",
            token,
            httponly=True,
            samesite="strict",
            max_age=43200,
            secure=os.environ.get("MADRID_SECURE_COOKIE", "0") == "1",
        )
        return {"ok": True}

    @app.post("/api/auth/logout", dependencies=protected)
    def sign_out(request: Request, response: Response, db: Session = Depends(session)) -> dict[str, bool]:
        db.execute(
            delete(LoginSession).where(
                LoginSession.token_hash == token_hash(request.cookies.get("madrid_session", ""))
            )
        )
        db.commit()
        response.delete_cookie("madrid_session")
        return {"ok": True}

    @app.get("/api/settings", dependencies=protected)
    def settings(db: Session = Depends(session)) -> dict[str, Any]:
        found = db.get(Setting, 1)
        return Rules.model_validate(found.values if found else {}).model_dump()

    @app.put("/api/settings", dependencies=protected)
    def update_settings(body: Rules, db: Session = Depends(session)) -> dict[str, Any]:
        found = db.get(Setting, 1)
        if found:
            found.values = body.model_dump()
        else:
            db.add(Setting(id=1, values=body.model_dump()))
        db.add(Audit(action="rules_updated", reason=json.dumps(body.model_dump(), sort_keys=True), at=now()))
        db.commit()
        return body.model_dump()

    @app.post("/api/imports", dependencies=protected)
    def upload(file: UploadFile = File(...), spec: str = Form(...)) -> dict[str, Any]:
        try:
            parsed = ImportSpec.model_validate_json(spec)
            content = file.file.read(MAX_BYTES + 1)
            batch = stage(factory, directory, file.filename or "upload", content, parsed)
            return redact_batch(batch)
        except (ValueError, ValidationError, subprocess.TimeoutExpired) as exc:
            if isinstance(exc, ValidationError):
                detail = "invalid_import_metadata"
            elif isinstance(exc, subprocess.TimeoutExpired):
                detail = "parser_timeout"
            else:
                detail = str(exc)[:160]
            raise HTTPException(422, detail) from exc

    @app.get("/api/batches", dependencies=protected)
    def batches(db: Session = Depends(session)) -> list[dict[str, Any]]:
        return [
            redact_batch(b, False) for b in db.scalars(select(Batch).order_by(Batch.created_at.desc())).all()
        ]

    @app.get("/api/batches/{batch_id}", dependencies=protected)
    def batch_detail(batch_id: str, db: Session = Depends(session)) -> dict[str, Any]:
        batch = db.get(Batch, batch_id)
        if not batch:
            raise HTTPException(404, "batch_not_found")
        return redact_batch(batch)

    @app.post("/api/batches/{batch_id}/action", dependencies=protected)
    def change_batch(batch_id: str, body: Action, db: Session = Depends(session)) -> dict[str, Any]:
        try:
            # Auth already started a read transaction; release it before the write lock.
            db.rollback()
            return redact_batch(transition(db, batch_id, body.action, body.reason))
        except ValueError as exc:
            db.rollback()
            raise HTTPException(409, str(exc)) from exc

    @app.get("/api/batches/{batch_id}/comparison", dependencies=protected)
    def batch_comparison(batch_id: str, db: Session = Depends(session)) -> dict[str, Any]:
        batch = db.get(Batch, batch_id)
        if not batch:
            raise HTTPException(404, "batch_not_found")
        return compare_batch(db, batch)

    def build_report(
        start: date, end: date, scope: str, db: Session, stock_asof: date | None = None
    ) -> dict[str, Any]:
        if end < start or (end - start).days > 1095:
            raise HTTPException(422, "invalid_or_excessive_period")
        rows = list(db.scalars(select(Batch).where(Batch.status == "accepted", Batch.scope == scope)).all())
        setting = db.get(Setting, 1)
        rules = Rules.model_validate(setting.values if setting else {})
        report = calculate(
            rows,
            start.isoformat(),
            end.isoformat(),
            scope,
            rules,
            stock_asof.isoformat() if stock_asof else None,
        )
        days = (end - start).days + 1
        prior = calculate(
            rows,
            (start - timedelta(days=days)).isoformat(),
            (start - timedelta(days=1)).isoformat(),
            scope,
            rules,
        )
        value, previous = report["metrics"]["net_sales"]["value"], prior["metrics"]["net_sales"]["value"]
        report["trend"] = {
            "prior_start": prior["period"]["start"],
            "prior_end": prior["period"]["end"],
            "net_sales_change": amount(
                (decimal_value(value) - decimal_value(previous)) / decimal_value(previous) * 100
                if value is not None
                and previous is not None
                and decimal_value(previous) > 0
                and report["currency"] == prior["currency"]
                else None,
                "comparable_complete_prior_period_required",
            ),
        }
        return report

    @app.get("/api/analytics", dependencies=protected)
    def analytics(
        start: date,
        end: date,
        scope: str = "store",
        stock_asof: date | None = None,
        db: Session = Depends(session),
    ) -> dict[str, Any]:
        return build_report(start, end, scope, db, stock_asof)

    @app.get("/api/exports/{kind}", dependencies=protected)
    def export(
        kind: str,
        start: date,
        end: date,
        scope: str = "store",
        stock_asof: date | None = None,
        db: Session = Depends(session),
    ) -> Response:
        if kind not in {"csv", "xlsx", "pdf"}:
            raise HTTPException(404, "unsupported_export")
        try:
            output = export_report(build_report(start, end, scope, db, stock_asof), kind)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        media = {
            "csv": "text/csv; charset=utf-8",
            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "pdf": "application/pdf",
        }[kind]
        return Response(
            output,
            media_type=media,
            headers={"Content-Disposition": f'attachment; filename="madrid-{start}-{end}.{kind}"'},
        )

    @app.get("/api/audit", dependencies=protected)
    def audit(db: Session = Depends(session)) -> list[dict[str, Any]]:
        return [
            {"id": a.id, "batch_id": a.batch_id, "action": a.action, "reason": a.reason, "at": a.at}
            for a in db.scalars(select(Audit).order_by(Audit.id.desc()).limit(1000)).all()
        ]

    @app.delete("/api/batches/{batch_id}/original", dependencies=protected)
    def delete_original(batch_id: str, body: Reason, db: Session = Depends(session)) -> dict[str, bool]:
        # Retention is explicit and never deletes normalized/audit history.
        db.rollback()
        lock_writes(db)
        batch = db.get(Batch, batch_id)
        if not batch or batch.status not in {"rejected", "rolled_back"} or not body.reason.strip():
            raise HTTPException(409, "only_inactive_sources_can_be_deleted_with_reason")
        shared = db.scalars(
            select(Batch).where(Batch.checksum == batch.checksum, Batch.status.in_(["staged", "accepted"]))
        ).first()
        if shared:
            raise HTTPException(409, "source_still_required")
        for path in (directory / "originals").glob(batch.checksum + ".*"):
            path.unlink()
        original = db.get(Original, batch.checksum + Path(batch.filename).suffix.lower())
        if original:
            db.delete(original)
        db.add(Audit(batch_id=batch.id, action="original_deleted", reason=body.reason, at=now()))
        db.commit()
        return {"ok": True}

    dist = ROOT / "frontend" / "dist"
    if dist.exists():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

        @app.get("/{path:path}")
        def ui(path: str) -> FileResponse:
            if path.startswith("api/"):
                raise HTTPException(404)
            file = (dist / path).resolve()
            if not file.is_relative_to(dist.resolve()) or not file.is_file():
                file = dist / "index.html"
            return FileResponse(file, headers={"Cache-Control": "no-cache"})

    return app
