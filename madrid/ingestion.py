from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from madrid.contracts import (
    CONTRACT_VERSION,
    PARSER_VERSION,
    ImportSpec,
    code_value,
    date_value,
    decimal_value,
)
from madrid.db import Audit, Batch, Original, lock_writes, private_dir

ALIASES = {
    "barcode": ["sku", "code", "product code", "الباركود", "باركود", "كود الصنف", "كود"],
    "name": ["product", "product name", "اسم الصنف", "الصنف", "اسم المنتج"],
    "category": ["التصنيف", "المجموعة", "القسم"],
    "quantity": ["qty", "on_hand", "الكمية", "الرصيد"],
    "reserved": ["المحجوز", "الكمية المحجوزة"],
    "available": ["المتاح", "صافي المتاح"],
    "sold": ["units_sold", "وحدات مباعة", "كمية البيع"],
    "returned": ["units_returned", "كمية المرتجع"],
    "rep": ["representative", "المندوب", "اسم المندوب"],
    "date": ["التاريخ"],
    "kind": ["transaction_type", "نوع الحركة"],
    "incoming": ["in_qty", "وارد"],
    "outgoing": ["out_qty", "صادر"],
    "gross": [],
    "discount": [],
    "return_value": [],
    "net": [],
    "cogs": [],
    "amount": [],
    "cost": [],
    "target": [],
    "reference": [],
    "running_balance": [],
    "introduced": [],
    "in_stock_days": [],
    "source_net_discount": [],
    "source_unit_price": [],
    "source_net_quantity": [],
    "source_signed_gross": [],
    "source_incoming_value": [],
    "source_outgoing_value": [],
    "source_running_value": [],
    "warehouse": [],
}
NUMBERS = {
    "quantity",
    "reserved",
    "available",
    "sold",
    "returned",
    "incoming",
    "outgoing",
    "gross",
    "discount",
    "return_value",
    "net",
    "cogs",
    "amount",
    "cost",
    "target",
    "running_balance",
    "in_stock_days",
    "source_net_discount",
    "source_net_quantity",
    "source_signed_gross",
    "source_incoming_value",
    "source_outgoing_value",
}
REQUIRED = {
    "snapshot": {"barcode", "name", "quantity"},
    "sales": {"barcode", "name", "sold", "returned"},
    "movement": {"barcode", "name", "date", "kind", "incoming", "outgoing"},
    "costs": {"barcode", "cost"},
    "expenses": {"date", "amount", "category"},
    "targets": {"rep", "target"},
}
MOVEMENTS = {
    "sale",
    "purchase",
    "sales_return",
    "purchase_return",
    "transfer_in",
    "transfer_out",
    "adjustment_in",
    "adjustment_out",
}


def now() -> str:
    return datetime.now(UTC).isoformat()


def header_key(value: str) -> str:
    return " ".join(value.strip().lower().replace("_", " ").split())


def columns(cells: list[str], spec: ImportSpec) -> dict[str, int]:
    result = {}
    for field, aliases in ALIASES.items():
        names = [spec.column_map[field]] if field in spec.column_map else [field, *aliases]
        indices = [i for i, c in enumerate(cells) if header_key(c) in {header_key(n) for n in names}]
        if len(indices) == 1:
            result[field] = indices[0]
    return result


def normalize(
    raw: list[dict[str, Any]], spec: ImportSpec
) -> tuple[list[dict[str, Any]], list[str], dict[str, Any]]:
    if raw and raw[0].get("adapter") == "arabic_pos_v1":
        from madrid.pos_contract import normalize_pos

        return normalize_pos(raw, spec, normalize)
    records: list[dict[str, Any]] = []
    issues: list[str] = []
    mapping: dict[str, int] = {}
    pending: dict[str, Any] | None = None
    total_rows: list[dict[str, Any]] = []
    current_sheet: str | None = None
    for occurrence, row in enumerate(raw):
        sheet = row["location"].get("sheet")
        if sheet != current_sheet:
            mapping = {}
            pending = None
            current_sheet = sheet
        cells = row["cells"]
        candidate = columns(cells, spec)
        entry: dict[str, Any] = {
            "raw": row,
            "occurrence": occurrence,
            "kind": "detail",
            "data": {},
            "issues": [],
        }
        if REQUIRED[spec.report_type] <= candidate.keys():
            mapping = candidate
            entry["kind"] = "header"
            records.append(entry)
            continue
        if not mapping:
            entry["kind"] = "unknown"
            entry["issues"].append("header_mapping_required")
            records.append(entry)
            continue
        data = {k: cells[i].strip() if i < len(cells) else "" for k, i in mapping.items()}
        labels = [header_key(c) for c in cells]
        if any(
            re.fullmatch(r"(total|grand total|subtotal|الإجمالي|الاجمالي|المجموع|إجمالي)(\s+.*)?", c)
            for c in labels
        ):
            entry["kind"] = "subtotal" if any(c.startswith("subtotal") for c in labels) else "total"
            entry["data"] = data
            total_rows.append(entry)
            records.append(entry)
            continue
        if spec.report_type not in {"expenses", "targets"} and data.get("barcode") and not data.get("name"):
            other = {v for k, v in data.items() if k != "barcode" and v}
            if pending and not other and not pending["data"].get("barcode"):
                pending["data"]["barcode"] = data["barcode"]
                pending["continuation"] = row["location"]
                entry["kind"] = "continuation"
                records.append(entry)
                continue
        entry["data"] = data
        if row.get("formula"):
            entry["issues"].append("workbook_formula_requires_review")
        if mapping.get("barcode") in row.get("numeric_columns", []):
            entry["issues"].append("numeric_barcode_requires_text_source")
        records.append(entry)
        pending = entry

    detail = [r for r in records if r["kind"] == "detail"]
    identities: set[str] = set()
    for record in detail:
        data = record["data"]
        try:
            if spec.report_type not in {"expenses", "targets"}:
                data["barcode"] = code_value(data.get("barcode", ""))
                if spec.report_type in {"snapshot", "costs"}:
                    if data["barcode"] in identities:
                        raise ValueError("duplicate_balance_or_cost_identity_requires_review")
                    identities.add(data["barcode"])
            for field in REQUIRED[spec.report_type]:
                if not str(data.get(field, "")).strip():
                    raise ValueError("missing_" + field)
            for field in NUMBERS & data.keys():
                if data[field] != "":
                    data[field] = str(decimal_value(data[field]))
                else:
                    del data[field]
            for field in ["date", "introduced"]:
                if data.get(field):
                    data[field] = date_value(data[field])
            if data.get("date") and not spec.start.isoformat() <= data["date"] <= spec.end.isoformat():
                raise ValueError("row_outside_report_period")
            if spec.report_type == "snapshot":
                if "reserved" in data and spec.reservation_verified:
                    available = decimal_value(data["quantity"]) - decimal_value(data["reserved"])
                    if "available" in data and available != decimal_value(data["available"]):
                        raise ValueError("available_stock_mismatch")
                    data["available"] = str(available)
                elif "available" in data and not spec.reservation_verified:
                    del data["available"]
            if spec.report_type == "sales":
                if any(decimal_value(data[k]) < 0 for k in ["sold", "returned"]):
                    raise ValueError("sales_quantities_must_be_nonnegative_magnitudes")
                data["net_quantity"] = str(decimal_value(data["sold"]) - decimal_value(data["returned"]))
                monetary = {"gross", "discount", "return_value", "net", "cogs"} & data.keys()
                if monetary and not spec.financial_verified:
                    raise ValueError("financial_semantics_not_confirmed")
                if any(
                    decimal_value(data[k]) < 0 for k in {"gross", "discount", "return_value"} & data.keys()
                ):
                    raise ValueError("sale_money_requires_nonnegative_magnitudes")
                if {"gross", "discount", "return_value"} <= data.keys():
                    value = (
                        decimal_value(data["gross"])
                        - decimal_value(data["discount"])
                        - decimal_value(data["return_value"])
                    )
                    if "net" in data and value != decimal_value(data["net"]):
                        raise ValueError("sales_money_relationship_mismatch")
                    data["net"] = str(value)
            if spec.report_type == "movement":
                if data["kind"] not in MOVEMENTS:
                    raise ValueError("unknown_movement_type")
                incoming, outgoing = decimal_value(data["incoming"]), decimal_value(data["outgoing"])
                if incoming < 0 or outgoing < 0 or (incoming > 0 and outgoing > 0):
                    raise ValueError("invalid_movement_direction_or_sign")
                if data["kind"] in {"sale", "purchase_return", "transfer_out", "adjustment_out"} and incoming:
                    raise ValueError("movement_type_direction_mismatch")
                if data["kind"] in {"purchase", "sales_return", "transfer_in", "adjustment_in"} and outgoing:
                    raise ValueError("movement_type_direction_mismatch")
                data["net_quantity"] = str(incoming - outgoing)
            if spec.report_type in {"costs", "expenses", "targets"}:
                field = {"costs": "cost", "expenses": "amount", "targets": "target"}[spec.report_type]
                if not spec.financial_verified or decimal_value(data[field]) < 0:
                    raise ValueError("verified_nonnegative_financial_input_required")
        except (ValueError, KeyError) as exc:
            record["issues"].append(str(exc).strip("'"))
    if not detail:
        issues.append("no_detail_records")
    if not spec.complete:
        issues.append("report_coverage_confirmation_required")
    if any(r["issues"] for r in records):
        issues.append("row_issues_require_corrected_reimport")
    totals: dict[str, Decimal] = {}
    sheet_totals: dict[str | None, dict[str, Decimal]] = {r["location"].get("sheet"): {} for r in raw}
    for record in detail:
        if record["issues"]:
            continue
        for field in (NUMBERS | {"net_quantity"}) - {"running_balance"}:
            if field in record["data"]:
                value = decimal_value(record["data"][field])
                totals[field] = totals.get(field, Decimal(0)) + value
                group = sheet_totals[record["raw"]["location"].get("sheet")]
                group[field] = group.get(field, Decimal(0)) + value
    primary = {
        "snapshot": "quantity",
        "sales": "net_quantity",
        "movement": "net_quantity",
        "costs": "cost",
        "expenses": "amount",
        "targets": "target",
    }[spec.report_type]
    expected = dict(spec.expected)
    # Each worksheet has its own headings and final footer; never compare its subtotal
    # against the combined workbook or inherit another worksheet's column positions.
    footers = [r for r in total_rows if r["kind"] == "total"]
    sheet_footers = {r["raw"]["location"].get("sheet"): r["data"] for r in footers}
    source_primary: dict[str | None, Decimal] = {}
    for sheet, raw_total in sheet_footers.items():
        try:
            if primary == "net_quantity":
                a, b = ("sold", "returned") if spec.report_type == "sales" else ("incoming", "outgoing")
                source_primary[sheet] = decimal_value(raw_total[a]) - decimal_value(raw_total[b])
            elif raw_total.get(primary):
                source_primary[sheet] = decimal_value(raw_total[primary])
        except (ValueError, KeyError):
            pass
    if primary not in expected and source_primary and source_primary.keys() == sheet_totals.keys():
        expected[primary] = str(sum(source_primary.values(), Decimal(0)))
    if primary not in expected:
        issues.append("independent_source_total_required:" + primary)
    if any("net" in r["data"] for r in detail) and "net" not in expected:
        issues.append("independent_source_total_required:net")
    checks = {
        k: {
            "expected": str(decimal_value(v)),
            "actual": str(totals.get(k, Decimal(0))),
            "matches": k in totals and decimal_value(v) == totals[k],
        }
        for k, v in expected.items()
    }
    for sheet, footer in sheet_footers.items():
        group = sheet_totals[sheet]
        prefix = "source_footer:" + (f"{sheet}:" if len(sheet_totals) > 1 else "")
        if sheet in source_primary:
            checks[prefix + primary] = {
                "expected": str(source_primary[sheet]),
                "actual": str(group.get(primary, Decimal(0))),
                "matches": primary in group and source_primary[sheet] == group[primary],
            }
        for field in (NUMBERS | {"net_quantity"}) & group.keys():
            if footer.get(field):
                try:
                    value = decimal_value(footer[field])
                    checks[prefix + field] = {
                        "expected": str(value),
                        "actual": str(group[field]),
                        "matches": value == group[field],
                    }
                except ValueError:
                    issues.append("invalid_source_footer_number:" + field)
    if any(not check["matches"] for check in checks.values()):
        issues.append("source_total_mismatch")
    return (
        records,
        sorted(set(issues)),
        {
            "totals": {k: str(v) for k, v in totals.items()},
            "checks": checks,
            "details": len(detail),
            "excluded": len(records) - len(detail),
        },
    )


def publish_original(file: Path, content: bytes, checksum: str) -> None:
    if not file.exists():
        temporary = file.with_name(uuid.uuid4().hex + ".tmp")
        try:
            with temporary.open("xb") as out:
                temporary.chmod(0o600)
                out.write(content)
                out.flush()
                os.fsync(out.fileno())
            try:
                os.link(temporary, file)
            except FileExistsError:
                pass
        finally:
            temporary.unlink(missing_ok=True)
    if hashlib.sha256(file.read_bytes()).hexdigest() != checksum:
        raise ValueError("stored_source_integrity_failure")


def extract_source(file: Path, suffix: str, options: dict[str, Any]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "madrid.extraction"],
        input=json.dumps({"path": str(file), "suffix": suffix, "options": options}),
        text=True,
        capture_output=True,
        timeout=35,
    )


def stage(factory: sessionmaker, directory: Path, filename: str, content: bytes, spec: ImportSpec) -> Batch:
    from madrid.extraction import MAX_BYTES

    if not content or len(content) > MAX_BYTES:
        raise ValueError("empty_or_oversized_file")
    suffix = Path(filename).suffix.lower()
    if suffix not in {".csv", ".xls", ".xlsx", ".pdf"}:
        raise ValueError("unsupported_file_type")
    checksum = hashlib.sha256(content).hexdigest()
    options = spec.model_dump(mode="json")
    identity = hashlib.sha256(
        json.dumps([checksum, options, PARSER_VERSION, CONTRACT_VERSION], sort_keys=True).encode()
    ).hexdigest()
    read_source_dates = suffix == ".pdf" and spec.source_dates == "report"
    if not read_source_dates:
        with factory() as session:
            existing = session.scalar(select(Batch).where(Batch.identity == identity))
            if existing:
                return existing
    remote = factory.kw["bind"].dialect.name == "postgresql"
    if remote:
        # Each invocation gets its own bounded parser scratch space. Originals commit with the batch.
        with tempfile.TemporaryDirectory(prefix="parse-", dir=directory) as temporary_directory:
            file = Path(temporary_directory) / (checksum + suffix)
            file.write_bytes(content)
            file.chmod(0o600)
            proc = extract_source(file, suffix, options)
    else:
        file = private_dir(directory / "originals") / (checksum + suffix)
        publish_original(file, content, checksum)
        proc = extract_source(file, suffix, options)
    try:
        result = json.loads(proc.stdout)
    except ValueError as exc:
        raise ValueError("parser_resource_limit_or_failure") from exc
    if proc.returncode or "error" in result:
        raise ValueError(result.get("error", "parser_failure"))
    if read_source_dates:
        first = result["rows"][0]
        if first.get("adapter") == "arabic_pos_v1":
            spec = ImportSpec.model_validate({**options, **first["source_period"]})
            options = spec.model_dump(mode="json")
        identity = hashlib.sha256(
            json.dumps([checksum, options, PARSER_VERSION, CONTRACT_VERSION], sort_keys=True).encode()
        ).hexdigest()
        with factory() as session:
            existing = session.scalar(select(Batch).where(Batch.identity == identity))
            if existing:
                return existing
    records, issues, reconciliation = normalize(result["rows"], spec)
    batch = Batch(
        id=uuid.uuid4().hex,
        identity=identity,
        filename=Path(filename).name[:200],
        checksum=checksum,
        report_type=spec.report_type,
        scope=spec.scope,
        start=spec.start.isoformat(),
        end=spec.end.isoformat(),
        status="staged",
        metadata_json={**options, "parser_version": PARSER_VERSION, "contract_version": CONTRACT_VERSION},
        rows=records,
        issues=issues,
        reconciliation=reconciliation,
        created_at=now(),
    )
    with factory() as session:
        lock_writes(session)
        if remote:
            original = session.get(Original, checksum + suffix)
            if original is None:
                session.add(Original(name=checksum + suffix, content=content))
            elif hashlib.sha256(original.content).hexdigest() != checksum:
                raise ValueError("stored_source_integrity_failure")
        else:
            publish_original(file, content, checksum)
        session.add(batch)
        try:
            session.flush()
            session.add(Audit(batch_id=batch.id, action="staged", reason="", at=now()))
            session.commit()
        except IntegrityError:
            session.rollback()
            existing = session.scalar(select(Batch).where(Batch.identity == identity))
            if existing:
                return existing
            raise
    return batch


def transition(session: Session, batch_id: str, action: str, reason: str) -> Batch:
    lock_writes(session)
    batch = session.get(Batch, batch_id)
    if not batch:
        raise ValueError("batch_not_found")
    if action == "accept":
        if batch.status != "staged" or batch.issues:
            raise ValueError("batch_not_validated")
        others = session.scalars(
            select(Batch).where(
                Batch.status == "accepted",
                Batch.scope == batch.scope,
                Batch.report_type == batch.report_type,
                Batch.start <= batch.end,
                Batch.end >= batch.start,
            )
        ).all()
        if others:
            raise ValueError("overlapping_accepted_coverage_rollback_explicitly_first")
        batch.status = "accepted"
    elif action == "reject" and batch.status == "staged" and reason.strip():
        batch.status = "rejected"
    elif action == "rollback" and batch.status == "accepted" and reason.strip():
        batch.status = "rolled_back"
    else:
        raise ValueError("invalid_transition_or_missing_reason")
    session.add(Audit(batch_id=batch.id, action=action, reason=reason[:1000], at=now()))
    session.commit()
    return batch


def compare_batch(session: Session, batch: Batch) -> dict[str, Any]:
    """Read-only comparison against accepted facts in the same coverage scope."""
    accepted = list(
        session.scalars(
            select(Batch).where(Batch.status == "accepted", Batch.scope == batch.scope, Batch.id != batch.id)
        ).all()
    )
    existing = {
        row["data"]["barcode"]
        for source in accepted
        for row in source.rows
        if row["kind"] == "detail" and row["data"].get("barcode")
    }
    incoming = {
        row["data"]["barcode"]
        for row in batch.rows
        if row["kind"] == "detail" and not row["issues"] and row["data"].get("barcode")
    }
    overlaps = [
        source
        for source in accepted
        if source.report_type == batch.report_type and source.start <= batch.end and source.end >= batch.start
    ]
    snapshots = [
        source for source in accepted if source.report_type == "snapshot" and source.end <= batch.end
    ]
    previous = max(snapshots, key=lambda source: source.end) if snapshots else None
    changes = []
    if previous and batch.report_type == "snapshot":
        prior = {row["data"]["barcode"]: row["data"] for row in previous.rows if row["kind"] == "detail"}
        for row in batch.rows:
            data = row["data"]
            if row["kind"] != "detail" or row["issues"] or data.get("barcode") not in prior:
                continue
            before = prior[data["barcode"]]
            if decimal_value(data["quantity"]) != decimal_value(before["quantity"]):
                changes.append(
                    {
                        "barcode": data["barcode"],
                        "name": data["name"],
                        "previous": before["quantity"],
                        "incoming": data["quantity"],
                        "difference": str(
                            decimal_value(data["quantity"]) - decimal_value(before["quantity"])
                        ),
                    }
                )
    return {
        "new_products": len(incoming - existing),
        "existing_products": len(incoming & existing),
        "changed_stock_products": len(changes),
        "stock_changes": changes[:20],
        "previous_snapshot_date": previous.end if previous else None,
        "overlaps": [
            {"id": source.id, "filename": source.filename, "start": source.start, "end": source.end}
            for source in overlaps
        ],
        "can_accept": batch.status == "staged" and not batch.issues and not overlaps,
    }
