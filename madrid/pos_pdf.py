"""Inspected Arabic POS layout: spatial cells + bounded PDFium logical Unicode.

No filename, employee, product, quantity or financial total identifies a profile.
Original cells remain immutable; all mapped values retain their physical locator.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pypdfium2 as pdfium

from madrid.contracts import date_value

PROFILE = "arabic_pos_v1"
TITLES = {"snapshot": "جرد المخازن", "sales": "مبيعات المندوبين", "movement": "حركة تفصيلية للمخازن"}
DATE = r"\d{1,2}/\d{1,2}/\d{4}"


def logical_cell(text: Any, page_height: float, bbox: Any) -> str:
    if bbox is None:
        return ""
    left, top, right, bottom = bbox
    return (
        str(text.get_text_bounded(left, page_height - bottom, right, page_height - top))
        .strip()
        .replace("\r\n", "\n")
    )


def extract_pos(pdf: Any, path: Path, options: dict[str, Any]) -> list[dict[str, Any]] | None:
    requested = options.get("pdf_profile", "auto")
    if requested == "generic":
        return None
    native = pdfium.PdfDocument(str(path))
    try:
        first_page = native[0]
        first_text = first_page.get_textpage()
        heading = first_text.get_text_bounded()
        first_text.close()
        first_page.close()
        detected = next((kind for kind, title in TITLES.items() if title in heading), None)
        if not detected:
            if requested == PROFILE:
                raise ValueError("pos_profile_signature_not_found")
            return None
        if detected != options["report_type"] and not options.get("inspect"):
            raise ValueError("source_report_type_mismatch")
        if options.get("column_map"):
            raise ValueError("pos_fixed_profile_requires_empty_column_map")
        if detected == "snapshot":
            period = re.search(r"جرد المخازن بتاريخ\s*(" + DATE + ")", heading)
            if not period:
                raise ValueError("source_snapshot_date_missing")
            start = end = date_value(period[1])
        else:
            period = re.search(r"من:\s*(" + DATE + r")\s*(?:الى|إلى):\s*(" + DATE + ")", heading)
            if not period:
                raise ValueError("source_report_period_missing")
            start, end = date_value(period[1]), date_value(period[2])
        if options.get("source_dates") != "report" and (start != options["start"] or end != options["end"]):
            raise ValueError("source_period_does_not_match_import_metadata")
        output: list[dict[str, Any]] = []
        for number, page in enumerate(pdf.pages, 1):
            native_page = native[number - 1]
            text_page = native_page.get_textpage()
            try:
                tables = page.find_tables()
                if not tables:
                    raise ValueError("pos_page_without_expected_table")
                lines = page.extract_text_lines()
                events = []
                for index, table in enumerate(tables, 1):
                    before = [line for line in lines if line["bottom"] <= table.bbox[1]]
                    label_line = max(before, key=lambda line: line["top"]) if before else None
                    context = ""
                    if label_line:
                        context = logical_cell(
                            text_page,
                            page.height,
                            (
                                label_line["x0"] - 1,
                                label_line["top"] - 1,
                                label_line["x1"] + 1,
                                label_line["bottom"] + 1,
                            ),
                        )
                    values = table.extract()
                    for row_no, (cells, geometry) in enumerate(zip(values, table.rows, strict=True), 1):
                        if len(cells) != {"snapshot": 7, "sales": 8, "movement": 11}[detected]:
                            raise ValueError("pos_table_column_shape_changed")
                        logical = [logical_cell(text_page, page.height, bbox) for bbox in geometry.cells]
                        if any(len(value or "") > 2000 for value in [*cells, *logical]):
                            raise ValueError("cell_text_limit")
                        events.append(
                            {
                                "cells": [c or "" for c in cells],
                                "logical_cells": logical,
                                "location": {"page": number, "table": index, "row": row_no},
                                "bbox": list(geometry.bbox),
                                "context": context,
                                "source_event": "table",
                                "top": geometry.bbox[1],
                            }
                        )
                for line in lines:
                    if any(table.bbox[1] <= line["top"] <= table.bbox[3] for table in tables):
                        continue
                    logical_line = logical_cell(
                        text_page,
                        page.height,
                        (line["x0"] - 1, line["top"] - 1, line["x1"] + 1, line["bottom"] + 1),
                    )
                    # Keep outside summaries: employee/region/grand totals lie outside the grid.
                    if (
                        "اجمالي" in logical_line
                        or "إجمالي" in logical_line
                        or re.search(r"\(\d{6,}\)", logical_line)
                    ):
                        prior = [event for event in events if event["top"] < line["top"]]
                        context = max(prior, key=lambda event: event["top"])["context"] if prior else ""
                        events.append(
                            {
                                "cells": [line["text"]],
                                "logical_cells": [logical_line],
                                "location": {"page": number, "line": round(line["top"], 3)},
                                "bbox": [line["x0"], line["top"], line["x1"], line["bottom"]],
                                "context": context,
                                "source_event": "outside",
                                "top": line["top"],
                            }
                        )
                for event in sorted(events, key=lambda event: event["top"]):
                    event.update(
                        {
                            "adapter": PROFILE,
                            "source_kind": detected,
                            "source_period": {"start": start, "end": end},
                            "numeric_columns": [],
                            "formula": False,
                        }
                    )
                    output.append(event)
            finally:
                text_page.close()
                native_page.close()
        if len(output) > 10000:
            raise ValueError("row_or_column_limit")
        return output
    finally:
        native.close()
