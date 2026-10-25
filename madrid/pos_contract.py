"""Normalize the inspected POS profile without assigning unproven money semantics."""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Callable
from decimal import Decimal
from typing import Any

from madrid.contracts import ImportSpec, decimal_value

FIELDS = {
    "snapshot": ["barcode", "name", "category", "quantity", "reserved", "available"],
    "sales": [
        "barcode",
        "name",
        "rep",
        "sold",
        "returned",
        "net",
        "source_net_discount",
        "source_unit_price",
        "source_net_quantity",
        "source_signed_gross",
    ],
    "movement": [
        "barcode",
        "name",
        "category",
        "warehouse",
        "date",
        "kind",
        "incoming",
        "outgoing",
        "running_balance",
        "source_incoming_value",
        "source_outgoing_value",
        "source_running_value",
        "reference",
    ],
}


def compact(value: str) -> str:
    return "".join(value.split()).replace("إ", "ا").replace("أ", "ا")


def product(value: str) -> tuple[str, str]:
    matches = list(re.finditer(r"\((\d{6,})\)", value))
    if len(matches) != 1:
        raise ValueError("pos_product_identifier_requires_review")
    match = matches[0]
    return match[1], " ".join((value[: match.start()] + value[match.end() :]).split())


def normalize_pos(
    raw: list[dict[str, Any]], spec: ImportSpec, normalize_generic: Callable[..., Any]
) -> tuple[list[dict[str, Any]], list[str], dict[str, Any]]:
    fields = FIELDS[spec.report_type]
    canonical = []
    classifications = []
    source_issues: dict[int, list[str]] = defaultdict(list)
    details: list[dict[str, str]] = []
    item: list[dict[str, str]] = []
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    previous: dict[tuple[str, str], dict[str, str]] = {}
    check_counts: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    observed_footer: dict[str, str] = {}

    def dec(value: str) -> str:
        return str(decimal_value(value))

    def verify(category: str, expected: dict[str, str], source: list[dict[str, str]], index: int) -> None:
        matches = True
        for field, value in expected.items():
            actual = sum((decimal_value(d[field]) for d in source), Decimal(0))
            if actual != decimal_value(value):
                source_issues[index].append("pos_" + category + "_mismatch:" + field)
                matches = False
        check_counts[category][0] += 1
        check_counts[category][1] += int(matches)

    for i, source in enumerate(raw):
        r, logical = source["cells"], source["logical_cells"]
        ctx = source["context"]
        data: dict[str, str] = {}
        kind = "note"
        try:
            if source["source_event"] == "outside":
                label = compact(logical[0])
                numbers = re.findall(r"-?\d+(?:,\d{3})*(?:\.\d+)?", r[0])
                if spec.report_type == "sales" and "اجمالي" in label:
                    if len(numbers) != 6:
                        raise ValueError("pos_sales_summary_shape_changed")
                    data = dict(
                        zip(
                            [
                                "net",
                                "source_net_discount",
                                "ignored_price",
                                "source_net_quantity",
                                "returned",
                                "sold",
                            ],
                            map(dec, numbers),
                            strict=True,
                        )
                    )
                    data.pop("ignored_price")
                    if "اجماليالمندوب" in label:
                        verify("representative_totals", data, grouped[ctx], i)
                        kind = "subtotal"
                    elif "اجماليكلالمناطق" in label or "اجماليالمنطقة" in label:
                        verify("report_totals", data, details, i)
                        kind = "total" if "اجماليكلالمناطق" in label else "subtotal"
                        observed_footer.update(
                            {"net": data["net"], "net_quantity": data["source_net_quantity"]}
                        )
                    else:
                        raise ValueError("pos_unrecognized_sales_summary")
                elif spec.report_type == "movement" and "اجماليالكل" in label:
                    if len(numbers) != 6:
                        raise ValueError("pos_movement_summary_shape_changed")
                    balance_value, outgoing_value, incoming_value, balance, outgoing, incoming = map(
                        dec, numbers
                    )
                    data = {
                        "incoming": incoming,
                        "outgoing": outgoing,
                        "source_incoming_value": incoming_value,
                        "source_outgoing_value": outgoing_value,
                    }
                    verify("report_totals", data, details, i)
                    if decimal_value(incoming) - decimal_value(outgoing) != decimal_value(
                        balance
                    ) or decimal_value(incoming_value) - decimal_value(outgoing_value) != decimal_value(
                        balance_value
                    ):
                        raise ValueError("pos_report_net_balance_mismatch")
                    observed_footer["net_quantity"] = balance
                    kind = "total"
                else:
                    raise ValueError("pos_unmapped_outside_data")
            elif spec.report_type == "snapshot":
                if compact(r[4]) == "دوكرابلا":
                    kind = "header"
                elif re.fullmatch(r"\d{6,}", r[4]):
                    data = {
                        "barcode": r[4],
                        "name": logical[5],
                        "category": logical[6],
                        "quantity": dec(r[2]),
                        "reserved": dec(r[1]),
                        "available": dec(r[0]),
                    }
                    kind = "detail"
                else:
                    nums = [part for cell in r for part in re.findall(r"-?\d+(?:,\d{3})*(?:\.\d+)?", cell)]
                    if len(nums) != 3:
                        raise ValueError("pos_snapshot_unknown_row")
                    data = dict(zip(["available", "reserved", "quantity"], map(dec, nums), strict=True))
                    verify("stock_totals", data, details, i)
                    observed_footer["quantity"] = data["quantity"]
                    kind = "total"
            elif spec.report_type == "sales":
                if compact(r[7]) == "فنصلا":
                    kind = "header"
                elif "اجماليالصنف" in compact(logical[7]):
                    data = {
                        "net": dec(r[0]),
                        "source_net_discount": dec(r[1]),
                        "source_net_quantity": dec(r[4]),
                        "returned": dec(r[5]),
                        "sold": dec(r[6]),
                    }
                    verify("item_subtotals", data, item, i)
                    item = []
                    kind = "subtotal"
                else:
                    barcode, name = product(logical[7])
                    data = {
                        "barcode": barcode,
                        "name": name,
                        "rep": ctx,
                        "sold": dec(r[6]),
                        "returned": dec(r[5]),
                        "net": dec(r[0]),
                        "source_net_discount": dec(r[1]),
                        "source_unit_price": dec(r[2]),
                        "source_net_quantity": dec(r[4]),
                    }
                    data["source_signed_gross"] = str(decimal_value(r[2]) * decimal_value(r[4]))
                    if decimal_value(r[6]) - decimal_value(r[5]) != decimal_value(r[4]):
                        raise ValueError("pos_sales_net_quantity_mismatch")
                    if decimal_value(data["source_signed_gross"]) - decimal_value(r[1]) != decimal_value(
                        r[0]
                    ):
                        raise ValueError("pos_sales_signed_discount_relationship_mismatch")
                    if not ctx:
                        raise ValueError("pos_representative_context_missing")
                    kind = "detail"
            else:
                if compact(r[10]) == "خيراتلا":
                    kind = "header"
                elif "اجماليالفئة" in compact(logical[6]):
                    data = {
                        "incoming": dec(r[5]),
                        "outgoing": dec(r[4]),
                        "source_incoming_value": dec(r[2]),
                        "source_outgoing_value": dec(r[1]),
                    }
                    verify("category_totals", data, grouped[ctx], i)
                    if decimal_value(r[5]) - decimal_value(r[4]) != decimal_value(r[3]) or decimal_value(
                        r[2]
                    ) - decimal_value(r[1]) != decimal_value(r[0]):
                        raise ValueError("pos_category_net_balance_mismatch")
                    kind = "subtotal"
                else:
                    barcode, name = product(logical[7])
                    operation = compact(logical[9])
                    incoming_qty, outgoing_qty = decimal_value(r[5]), decimal_value(r[4])
                    if "فاتورةمردودمبيعات" in operation:
                        movement = "sales_return"
                    elif "فاتورةمردودمشتريات" in operation:
                        movement = "purchase_return"
                    elif "فاتورةمبيعات" in operation:
                        movement = "sale"
                    elif "فاتورةمشتريات" in operation:
                        movement = "purchase"
                    elif "تحويلمخزني" in operation:
                        movement = "transfer_in" if incoming_qty > 0 else "transfer_out"
                    elif "تسويةمخزنية" in operation:
                        movement = "adjustment_in" if incoming_qty > 0 else "adjustment_out"
                    else:
                        raise ValueError("pos_unknown_transaction_type")
                    reference = re.search(r"[A-Za-z]+\.?\d+", r[9])
                    if not reference:
                        raise ValueError("pos_document_reference_missing")
                    data = {
                        "barcode": barcode,
                        "name": name,
                        "category": ctx,
                        "warehouse": logical[8],
                        "date": r[10],
                        "kind": movement,
                        "incoming": dec(r[5]),
                        "outgoing": dec(r[4]),
                        "running_balance": dec(r[3]),
                        "source_incoming_value": dec(r[2]),
                        "source_outgoing_value": dec(r[1]),
                        "source_running_value": dec(r[0]),
                        "reference": reference[0],
                    }
                    key = barcode, logical[8]
                    if key in previous:
                        prev = previous[key]
                        checks = [
                            decimal_value(prev["running_balance"]) + incoming_qty - outgoing_qty
                            == decimal_value(r[3]),
                            decimal_value(prev["source_running_value"])
                            + decimal_value(r[2])
                            - decimal_value(r[1])
                            == decimal_value(r[0]),
                        ]
                        for label, matches in zip(
                            ["running_quantity_chain", "running_value_chain"], checks, strict=True
                        ):
                            check_counts[label][0] += 1
                            check_counts[label][1] += int(matches)
                            if not matches:
                                source_issues[i].append("pos_" + label + "_mismatch")
                    previous[key] = data
                    kind = "detail"
            if kind == "detail":
                details.append(data)
                grouped[ctx].append(data)
                if spec.report_type == "sales":
                    item.append(data)
            if kind == "header":
                cells = fields.copy()
            else:
                cells = [data.get(f, "") for f in fields]
                if kind in {"subtotal", "total", "note"}:
                    cells[0] = "TOTAL" if kind == "total" else "SUBTOTAL"
        except (ValueError, KeyError, IndexError) as exc:
            source_issues[i].append(str(exc))
            cells = [""] * len(fields)
            kind = "unknown"
        canonical.append(
            {"cells": cells, "location": source["location"], "numeric_columns": [], "formula": False}
        )
        classifications.append(kind)
    if not observed_footer:
        source_issues[0].append("pos_independent_report_footer_missing")
    effective = spec.model_copy(update={"expected": {**observed_footer, **spec.expected}})
    records, issues, reconciliation = normalize_generic(canonical, effective)
    for i, entry in enumerate(records):
        entry["raw"] = raw[i]
        entry["kind"] = classifications[i]
        entry["issues"].extend(source_issues.get(i, []))
    if source_issues:
        issues.append("pos_source_validation_failed")
    for label, (expected, actual) in check_counts.items():
        reconciliation["checks"]["source:" + label] = {
            "expected": str(expected),
            "actual": str(actual),
            "matches": expected == actual,
        }
    reconciliation["profile"] = "arabic_pos_v1"
    reconciliation["source_period"] = raw[0]["source_period"]
    reconciliation["source_validation"] = {
        key: {"checked": value[0], "passed": value[1]} for key, value in check_counts.items()
    }
    return records, sorted(set(issues)), reconciliation
