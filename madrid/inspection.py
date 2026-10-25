"""Read-only structural inspection; recognition does not imply reconciliation."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from madrid.contracts import CONTRACT_VERSION, PARSER_VERSION, ImportSpec
from madrid.extraction import MAX_BYTES
from madrid.ingestion import REQUIRED, columns


def summarize(raw: list[dict[str, Any]]) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in raw:
        key = str(row["location"].get("sheet", "PDF" if "page" in row["location"] else "CSV"))
        groups.setdefault(key, []).append(row)
    sheets = []
    numeric_barcode = False
    for name, rows in groups.items():
        header = rows[0]
        detected = None
        mapping: dict[str, int] = {}
        for row in rows[:50]:
            for kind, required in REQUIRED.items():
                spec = ImportSpec.model_validate(
                    {"report_type": kind, "start": "2000-01-01", "end": "2000-01-01"}
                )
                candidate = columns(row["cells"], spec)
                if required <= candidate.keys():
                    header, detected, mapping = row, kind, candidate
                    break
            if detected:
                break
        profiled = rows[0].get("adapter") == "arabic_pos_v1"
        numeric_barcode = numeric_barcode or any(
            mapping.get("barcode") in row.get("numeric_columns", []) for row in rows
        )
        detected = rows[0].get("source_kind", detected) if profiled else detected
        offset = rows.index(header) + 1 if detected and not profiled else 1
        sheets.append(
            {
                "name": name,
                "report_type": detected,
                "status": "RECOGNIZED" if detected or profiled else "NEEDS_MAPPING",
                "columns": header.get("logical_cells", header["cells"]),
                "header_location": header["location"],
                "mapping": {field: header["cells"][index] for field, index in mapping.items()},
                "preview": [row.get("logical_cells", row["cells"]) for row in rows[offset : offset + 5]],
                "rows": len(rows),
            }
        )
    warnings = []
    if any(row.get("formula") for row in raw):
        warnings.append("workbook_formula_requires_review")
    if numeric_barcode:
        warnings.append("numeric_barcode_requires_text_source")
    status = (
        "NEEDS_MAPPING"
        if any(sheet["status"] == "NEEDS_MAPPING" for sheet in sheets)
        else ("NEEDS_REVIEW" if warnings else "RECOGNIZED")
    )
    return {
        "status": status,
        "sheets": sheets,
        "issues": warnings,
        "pages": len({row["location"]["page"] for row in raw if "page" in row["location"]}),
        "source_period": raw[0].get("source_period"),
        "profile": raw[0].get("adapter", "structural"),
    }


def inspect_source(filename: str, content: bytes, options: dict[str, Any]) -> dict[str, Any]:
    suffix = Path(filename).suffix.lower()
    base = {
        "filename": Path(filename).name[:200],
        "size": len(content),
        "format": suffix.lstrip("."),
        "checksum": hashlib.sha256(content).hexdigest(),
        "parser_version": PARSER_VERSION,
        "contract_version": CONTRACT_VERSION,
        "sheets": [],
        "pages": 0,
    }
    if not content or len(content) > MAX_BYTES:
        return {**base, "status": "INVALID", "issues": ["empty_or_oversized_file"]}
    if suffix not in {".csv", ".xls", ".xlsx", ".pdf"}:
        return {**base, "status": "UNSUPPORTED", "issues": ["unsupported_file_type"]}
    with tempfile.TemporaryDirectory(prefix="madrid-inspect-") as temporary:
        path = Path(temporary) / ("source" + suffix)
        path.write_bytes(content)
        path.chmod(0o600)
        try:
            worker = subprocess.run(
                [sys.executable, "-m", "madrid.extraction"],
                input=json.dumps({"path": str(path), "suffix": suffix, "options": options, "inspect": True}),
                text=True,
                encoding="utf-8",
                capture_output=True,
                timeout=35,
            )
        except subprocess.TimeoutExpired:
            return {**base, "status": "UNSUPPORTED", "issues": ["parser_timeout"]}
    try:
        result = json.loads(worker.stdout)
    except ValueError:
        result = {"error": "parser_resource_limit_or_failure"}
    if worker.returncode or "error" in result:
        error = result.get("error", "parser_resource_limit_or_failure")
        review = error in {
            "source_report_type_mismatch",
            "csv_delimiter_requires_selection",
            "UnicodeDecodeError",
        }
        unsupported = error in {"pdf_layout_requires_adapter_no_table_or_text_layer", "parser_timeout"}
        return {
            **base,
            "status": "NEEDS_REVIEW" if review else "UNSUPPORTED" if unsupported else "INVALID",
            "issues": [error],
        }
    return {**base, **result}
