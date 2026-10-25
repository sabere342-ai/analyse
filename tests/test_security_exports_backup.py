import hashlib
import io
import json
import sqlite3

import pytest
from cryptography.exceptions import InvalidTag
from fastapi.testclient import TestClient
from openpyxl import load_workbook
from test_imports import SNAPSHOT, accept, upload

from madrid.app import create_app
from madrid.backup import create_backup, restore_backup
from madrid.reporting import safe_text


def test_auth_csrf_and_origin(tmp_path):
    with TestClient(create_app(tmp_path / "private")) as c:
        assert c.get("/api/batches").status_code == 401
        assert c.get("/api/exports/csv?start=2026-10-01&end=2026-10-23").status_code == 401
        assert c.post("/api/auth/setup", json={"password": "long-test-password"}).status_code == 403
        assert (
            c.post(
                "/api/auth/setup",
                headers={"X-Requested-With": "Madrid", "Origin": "https://evil.example"},
                json={"password": "long-test-password"},
            ).status_code
            == 403
        )
        assert c.get("/api/health").headers["cache-control"] == "no-store"
        assert c.get("/api/health", headers={"host": "evil.example"}).status_code == 400


def test_owner_setup_single_use_logout_and_rate_limit(client):
    assert client.post("/api/auth/setup", json={"password": "other-test-password"}).status_code == 409
    cookie = client.cookies.get("madrid_session")
    assert cookie
    assert client.post("/api/auth/logout").status_code == 200
    assert client.get("/api/batches").status_code == 401
    for _ in range(10):
        assert client.post("/api/auth/login", json={"password": "wrong-test-password"}).status_code == 401
    assert client.post("/api/auth/login", json={"password": "wrong-test-password"}).status_code == 429


@pytest.mark.parametrize(
    "payload", ["=1+1", "+cmd", "-cmd", "@SUM(1)", "\t=1+1", " \r\n=1+1", "\nanything", " \u200b=1+1"]
)
def test_formula_injection_neutralized(payload):
    assert safe_text(payload).startswith("'")


def test_exports_preserve_codes_and_totals_and_pdf_arabic(client):
    rows = [r[:] for r in SNAPSHOT]
    rows[1][1] = "=1+1"
    b = upload(client, rows)
    accept(client, b)
    query = "?start=2026-10-01&end=2026-10-24"
    csv = client.get("/api/exports/csv" + query)
    assert csv.status_code == 200 and "000366" in csv.text and "'=1+1" in csv.text
    xlsx = client.get("/api/exports/xlsx" + query)
    book = load_workbook(io.BytesIO(xlsx.content))
    cells = list(book.active.values)
    assert any(row[2] == "000366" and row[3] == "stock" and row[4] == "10" for row in cells)
    assert all(cell.data_type != "f" for row in book.active for cell in row)
    assert any(row[1] == "=1+1" for row in cells)
    assert any(cell.value == "000366" and cell.data_type == "s" for row in book.active for cell in row)
    pdf = client.get("/api/exports/pdf" + query)
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF-")
    import pdfplumber

    with pdfplumber.open(io.BytesIO(pdf.content)) as document:
        text = "".join(page.extract_text() or "" for page in document.pages)
        assert "000366" in text and len(document.pages) >= 1


def test_backup_encryption_hashes_restore_and_no_overwrite(client, tmp_path):
    b = upload(client, SNAPSHOT)
    accept(client, b)
    directory = client.app.state.directory
    password = "synthetic-backup-passphrase"
    content = create_backup(directory, password)
    assert b"000366" not in content
    destination = tmp_path / "restored"
    manifest = restore_backup(content, destination, password)
    with sqlite3.connect(destination / "madrid.sqlite3") as db:
        assert db.execute("SELECT status FROM batches").fetchone()[0] == "accepted"
        rows = json.loads(db.execute("SELECT rows FROM batches").fetchone()[0])
        assert rows[1]["data"]["barcode"] == "000366"
        assert db.execute("SELECT count(*) FROM sessions").fetchone()[0] == 0
    for name, checksum in manifest.items():
        # Sessions are deliberately invalidated after validating the restored DB manifest.
        if name != "madrid.sqlite3":
            assert hashlib.sha256((destination / name).read_bytes()).hexdigest() == checksum
    with pytest.raises(ValueError):
        restore_backup(content, destination, password)
    with pytest.raises(InvalidTag):
        restore_backup(content, tmp_path / "wrong", "wrong-passphrase-long")
    with TestClient(create_app(destination), headers={"X-Requested-With": "Madrid"}) as restored:
        assert (
            restored.post("/api/auth/login", json={"password": "synthetic-test-password-only"}).status_code
            == 200
        )
        report = restored.get("/api/analytics?start=2026-10-01&end=2026-10-24").json()
        assert report["metrics"]["stock"]["value"] == "10.00"


def test_all_templates_are_synthetic_and_work(client):
    for kind in ["snapshot", "sales", "movement", "costs", "expenses", "targets"]:
        response = client.get("/api/templates/" + kind)
        assert response.status_code == 200
        spec = {
            "report_type": kind,
            "start": "2026-10-01",
            "end": "2026-10-01",
            "complete": True,
            "financial_verified": True,
            "reservation_verified": True,
        }
        if kind == "sales":
            spec["expected"] = {"net": "180"}
        result = client.post(
            "/api/imports",
            files={"file": ("synthetic.csv", response.content)},
            data={"spec": json.dumps(spec)},
        )
        assert result.status_code == 200, result.text
        assert result.json()["issues"] == [], (kind, result.json()["issues"])


def test_original_retention_is_explicit_and_active_data_protected(client):
    b = upload(client, SNAPSHOT)
    url = f"/api/batches/{b['id']}/original"
    assert client.request("DELETE", url, json={"reason": "synthetic retention"}).status_code == 409
    assert (
        client.post(
            f"/api/batches/{b['id']}/action", json={"action": "reject", "reason": "synthetic rejection"}
        ).status_code
        == 200
    )
    assert client.request("DELETE", url, json={"reason": "synthetic retention"}).status_code == 200
    assert client.get(f"/api/batches/{b['id']}").json()["rows"]


def test_backup_fails_for_corrupt_required_original(client):
    b = upload(client, SNAPSHOT)
    accept(client, b)
    original = client.app.state.directory / "originals" / (b["checksum"] + ".csv")
    original.write_bytes(b"synthetic tamper")
    with pytest.raises(ValueError, match="backup_source_integrity_failure"):
        create_backup(client.app.state.directory, "synthetic-backup-passphrase")


def test_cloud_container_refuses_ephemeral_database_fallback(monkeypatch):
    from madrid.app import create_app

    monkeypatch.setenv("MADRID_REQUIRE_CLOUD_DATABASE", "1")
    monkeypatch.delenv("MADRID_DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError, match="durable_cloud_database_required"):
        create_app()


@pytest.mark.parametrize("variable", ["VERCEL_URL", "VERCEL_BRANCH_URL"])
def test_preview_origin_uses_only_validated_platform_hostname(client, monkeypatch, variable):
    from conftest import PASSWORD

    monkeypatch.setenv(variable, "madrid-preview-check.vercel.app")
    good = client.post(
        "/api/auth/login",
        json={"password": PASSWORD},
        headers={"Origin": "https://madrid-preview-check.vercel.app"},
    )
    assert good.status_code == 200
    bad = client.post(
        "/api/auth/login",
        json={"password": PASSWORD},
        headers={"Origin": "https://madrid-preview-check.vercel.app.evil.invalid"},
    )
    assert bad.status_code == 403 and bad.json()["detail"] == "origin_not_allowed"
    monkeypatch.setenv(variable, "madrid-preview-check.vercel.app.evil.invalid")
    still_bad = client.post(
        "/api/auth/login",
        json={"password": PASSWORD},
        headers={"Origin": "https://madrid-preview-check.vercel.app.evil.invalid"},
    )
    assert still_bad.status_code == 403
