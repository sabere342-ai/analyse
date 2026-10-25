from madrid.contracts import ImportSpec
from madrid.ingestion import normalize


def raw(cells, *, logical=None, context="مندوب تجريبي", event="table", row=1):
    return {
        "adapter": "arabic_pos_v1",
        "cells": cells,
        "logical_cells": logical or cells,
        "context": context,
        "source_event": event,
        "location": {"page": 1, "table": 1, "row": row},
        "source_period": {"start": "2026-01-01", "end": "2026-01-02"},
    }


def test_signed_net_discount_is_not_split_into_invented_returns_or_sale_discounts():
    rows = [
        raw(["", "", "", "", "", "", "", "فنصلا"]),
        raw(["-40", "-60", "100", "قطعة", "-1", "1", "0", "Synthetic\n(001007)"], row=2),
        raw(["-40", "-60", "0", "", "-1", "1", "0", "اجمالي الصنف"], row=3),
        raw(["-40 -60 0 -1 1 0 اجمالي المندوب"], event="outside", row=4),
        raw(["-40 -60 0 -1 1 0 اجمالي كل المناطق"], event="outside", row=5),
    ]
    spec = ImportSpec(
        report_type="sales", start="2026-01-01", end="2026-01-02", complete=True, financial_verified=True
    )
    records, issues, recon = normalize(rows, spec)
    assert not issues and recon["totals"]["net"] == "-40"
    detail = next(r["data"] for r in records if r["kind"] == "detail")
    assert detail["source_net_discount"] == "-60" and detail["net_quantity"] == "-1"
    assert not {"gross", "discount", "return_value", "cogs"} & detail.keys()
    assert records[1]["raw"]["cells"] == rows[1]["cells"]


def test_pos_subtotal_and_row_arithmetic_mismatches_block_acceptance():
    rows = [
        raw(["", "", "", "", "", "", "", "فنصلا"]),
        raw(["40", "60", "100", "قطعة", "1", "0", "1", "Synthetic\n(001007)"], row=2),
        raw(["41", "60", "100", "", "1", "0", "1", "اجمالي الصنف"], row=3),
        raw(["40 60 100 1 0 1 اجمالي كل المناطق"], event="outside", row=4),
    ]
    spec = ImportSpec(
        report_type="sales", start="2026-01-01", end="2026-01-02", complete=True, financial_verified=True
    )
    _, issues, recon = normalize(rows, spec)
    assert "pos_source_validation_failed" in issues
    assert not recon["checks"]["source:item_subtotals"]["matches"]
    rows[2]["cells"][0] = "40"
    rows[1]["cells"][1] = "50"
    _, issues, _ = normalize(rows, spec)
    assert issues


def test_pos_legitimate_price_occurrences_share_one_subtotal_without_deduplication():
    rows = [
        raw(["", "", "", "", "", "", "", "فنصلا"]),
        raw(["40", "60", "100", "قطعة", "1", "0", "1", "Synthetic\n(001007)"], row=2),
        raw(["70", "130", "200", "قطعة", "1", "0", "1", "Synthetic\n(001007)"], row=3),
        raw(["110", "190", "150", "", "2", "0", "2", "اجمالي الصنف"], row=4),
        raw(["110 190 150 2 0 2 اجمالي كل المناطق"], event="outside", row=5),
    ]
    spec = ImportSpec(
        report_type="sales", start="2026-01-01", end="2026-01-02", complete=True, financial_verified=True
    )
    _, issues, recon = normalize(rows, spec)
    assert not issues and recon["details"] == 2
    assert recon["source_validation"]["item_subtotals"] == {"checked": 1, "passed": 1}
