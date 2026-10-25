import pytest
from test_imports import SNAPSHOT, accept, upload

SALES = [
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
    ["000366", "تي شيرت", "ملابس", "مندوب تجريبي", "2", "1", "200", "20", "45", "135", "75"],
    ["TOTAL", "", "", "", "2", "1", "200", "20", "45", "135", "75"],
]
QUERY = "/api/analytics?start=2026-10-01&end=2026-10-23"


def sales(client, rows=SALES, **kwargs):
    batch = upload(
        client,
        rows,
        "sales",
        "2026-10-01",
        "2026-10-23",
        expected={"net_quantity": "1", "net": "135"},
        financial_verified=True,
        **kwargs,
    )
    accept(client, batch)
    return batch


def test_decimal_finance_expenses_targets_and_source_provenance(client):
    a = sales(client)
    expense = upload(
        client,
        [["date", "category", "amount"], ["01/10/2026", "تجريبي", "10"], ["", "TOTAL", "10"]],
        "expenses",
        "2026-10-01",
        "2026-10-23",
        financial_verified=True,
    )
    accept(client, expense)
    target = upload(
        client,
        [["rep", "target"], ["مندوب تجريبي", "100"], ["TOTAL", "100"]],
        "targets",
        "2026-10-01",
        "2026-10-23",
        financial_verified=True,
    )
    accept(client, target)
    report = client.get(QUERY).json()
    m = report["metrics"]
    for key, value in {
        "gross_sales": "200.00",
        "net_sales": "135.00",
        "cogs": "75.00",
        "gross_profit": "60.00",
        "gross_margin": "44.44",
        "expenses": "10.00",
        "operating_profit": "50.00",
    }.items():
        assert m[key]["value"] == value
    rep = report["representatives"][0]
    assert rep["return_rate"]["value"] == "50.00"
    assert rep["discount_rate"]["value"] == "10.00"
    assert rep["target_achievement"]["value"] == "135.00"
    assert report["products"][0]["evidence"][0]["batch_id"] == a["id"]
    assert report["recommendations"][0]["evidence"]


def test_costs_are_not_historical_cogs_and_expenses_not_zero(client):
    rows = [r[:-1] for r in SALES]
    sales(client, rows)
    cost = upload(
        client,
        [["barcode", "cost"], ["000366", "20"], ["TOTAL", "20"]],
        "costs",
        "2026-10-23",
        financial_verified=True,
    )
    accept(client, cost)
    stock = upload(client, SNAPSHOT, start="2026-10-23", reservation_verified=True)
    accept(client, stock)
    m = client.get(QUERY).json()["metrics"]
    assert m["net_sales"]["value"] == "135.00"
    assert m["cogs"]["value"] is None
    assert m["gross_profit"]["value"] is None
    assert m["expenses"]["value"] is None
    assert m["operating_profit"]["value"] is None
    assert m["inventory_cost_value"]["value"] == "200.00"


def test_discount_semantics_and_arithmetic_block_acceptance(client):
    unverified = upload(
        client, SALES, "sales", "2026-10-01", "2026-10-23", expected={"net_quantity": "1", "net": "135"}
    )
    assert "row_issues_require_corrected_reimport" in unverified["issues"]
    wrong = [r[:] for r in SALES]
    wrong[1][9] = "155"
    batch = upload(
        client,
        wrong,
        "sales",
        "2026-10-01",
        "2026-10-23",
        financial_verified=True,
        expected={"net_quantity": "1", "net": "155"},
    )
    assert "sales_money_relationship_mismatch" in batch["rows"][1]["issues"]


def test_movement_transfers_returns_and_balances_are_not_sales(client):
    rows = [
        ["barcode", "name", "date", "kind", "incoming", "outgoing", "running_balance"],
        ["000366", "تجريبي", "01/10/2026", "transfer_out", "0", "4", "96"],
        ["000366", "تجريبي", "02/10/2026", "sales_return", "2", "0", "98"],
        ["TOTAL", "", "", "", "2", "4", ""],
    ]
    batch = upload(client, rows, "movement", "2026-10-01", "2026-10-23")
    assert batch["reconciliation"]["totals"]["net_quantity"] == "-2"
    accept(client, batch)
    report = client.get(QUERY).json()
    assert report["metrics"]["net_sales"]["value"] is None
    assert report["metrics"]["sold"]["value"] is None
    assert report["metrics"]["stock"]["value"] is None
    assert report["categories"][0]["incoming"] == "2"
    assert report["categories"][0]["outgoing"] == "4"


@pytest.mark.parametrize(
    "kind,incoming,outgoing",
    [("sale", "1", "0"), ("purchase", "0", "1"), ("sale", "0", "-1"), ("unknown", "1", "0")],
)
def test_invalid_movement_signs_and_types_reviewed(client, kind, incoming, outgoing):
    rows = [
        ["barcode", "name", "date", "kind", "incoming", "outgoing"],
        ["0001", "X", "01/10/2026", kind, incoming, outgoing],
    ]
    b = upload(client, rows, "movement", "2026-10-01", "2026-10-23", expected={"net_quantity": "0"})
    assert b["issues"]


def test_partial_period_is_not_zero_and_no_prorating(client):
    sales(client)
    report = client.get("/api/analytics?start=2026-10-05&end=2026-10-15").json()
    assert not report["sales_complete"]
    assert report["metrics"]["net_sales"]["value"] is None
    assert any("مجمعة" in w for w in report["warnings"])


def test_positive_stock_zero_sales_not_dead_for_new_product(client):
    sales(client)
    stock = upload(
        client,
        [
            ["barcode", "name", "quantity", "introduced"],
            ["000369", "منتج جديد", "5", "22/10/2026"],
            ["TOTAL", "", "5", ""],
        ],
        start="2026-10-23",
    )
    accept(client, stock)
    report = client.get(QUERY).json()
    product = next(p for p in report["products"] if p["barcode"] == "000369")
    assert product["sold"] == "0"
    assert product["classification"] == "zero_sales"
    assert product["coverage"]["value"] is None
    assert product["availability_adjusted_velocity"]["value"] is None


def test_missing_sales_feed_not_zero(client):
    stock = upload(client, SNAPSHOT, start="2026-10-23")
    accept(client, stock)
    product = client.get(QUERY).json()["products"][0]
    assert product["sold"] is None and product["classification"] == "insufficient_history"


def test_stockout_adjusted_velocity_and_replenishment(client):
    rows = [
        ["barcode", "name", "sold", "returned", "in_stock_days"],
        ["000366", "تجريبي", "20", "0", "10"],
        ["TOTAL", "", "20", "0", ""],
    ]
    batch = upload(client, rows, "sales", "2026-10-01", "2026-10-23", availability_verified=True)
    accept(client, batch)
    stock = upload(
        client,
        [
            ["barcode", "name", "quantity", "reserved", "introduced"],
            ["000366", "تجريبي", "1", "0", "01/09/2026"],
            ["TOTAL", "", "1", "0", ""],
        ],
        start="2026-10-23",
        reservation_verified=True,
    )
    accept(client, stock)
    report = client.get(QUERY).json()
    p = report["products"][0]
    assert p["availability_adjusted_velocity"]["value"] == "2.00"
    assert p["velocity"]["value"] == "0.87"
    assert p["classification"] == "insufficient_history"
    assert any(rec["action"] == "راجع إعادة التوريد" for rec in report["recommendations"])
    assert all(
        set(["subject", "observation", "evidence", "impact", "action", "quality"]) <= rec.keys()
        for rec in report["recommendations"]
    )


def test_stale_snapshot_blocks_replenishment(client):
    sales(client)
    stock = upload(client, SNAPSHOT, start="2026-10-22", reservation_verified=True)
    accept(client, stock)
    p = client.get(QUERY).json()["products"][0]
    assert p["coverage"]["value"] is None and p["replenishment_units"] is None


def test_financial_category_aggregation_uses_unrounded_values(client):
    rows = [
        ["barcode", "name", "category", "sold", "returned", "net"],
        ["0001", "A", "X", "1", "0", "0.005"],
        ["0002", "B", "X", "1", "0", "0.005"],
        ["TOTAL", "", "", "2", "0", "0.010"],
    ]
    b = upload(
        client,
        rows,
        "sales",
        "2026-10-01",
        "2026-10-23",
        financial_verified=True,
        expected={"net_quantity": "2", "net": "0.010"},
    )
    accept(client, b)
    r = client.get(QUERY).json()
    assert r["metrics"]["net_sales"]["value"] == "0.01"
    assert r["categories"][0]["net_sales"]["value"] == "0.01"


def test_negative_returns_only_and_zero_denominators(client):
    rows = [
        ["barcode", "name", "rep", "sold", "returned", "gross", "discount", "return_value", "net", "cogs"],
        ["000366", "A", "R", "0", "2", "0", "0", "100", "-100", "-50"],
        ["TOTAL", "", "", "0", "2", "0", "0", "100", "-100", "-50"],
    ]
    b = upload(
        client,
        rows,
        "sales",
        "2026-10-01",
        "2026-10-23",
        financial_verified=True,
        expected={"net_quantity": "-2", "net": "-100"},
    )
    accept(client, b)
    r = client.get(QUERY).json()
    assert r["metrics"]["gross_profit"]["value"] == "-50.00"
    assert r["metrics"]["gross_margin"]["value"] is None
    assert r["representatives"][0]["return_rate"]["value"] is None
    import csv
    import io

    exported = client.get("/api/exports/csv?start=2026-10-01&end=2026-10-23")
    values = list(csv.reader(io.StringIO(exported.content.decode("utf-8-sig"))))
    assert any(row[0] == "summary" and row[3] == "net_sales" and row[4] == "-100.00" for row in values)


def test_financial_recommendations_and_comparable_trend(client):
    sales(client)
    expense = upload(
        client,
        [["date", "category", "amount"], ["01/10/2026", "تجريبي", "100"], ["", "TOTAL", "100"]],
        "expenses",
        "2026-10-01",
        "2026-10-23",
        financial_verified=True,
    )
    accept(client, expense)
    previous = upload(
        client,
        SALES,
        "sales",
        "2026-09-08",
        "2026-09-30",
        expected={"net_quantity": "1", "net": "135"},
        financial_verified=True,
    )
    accept(client, previous)
    report = client.get(QUERY).json()
    assert report["metrics"]["operating_profit"]["value"] == "-40.00"
    assert any(r["action"] == "راجع المصروفات وتكلفة البيع" for r in report["recommendations"])
    assert report["trend"]["net_sales_change"]["value"] == "0.00"


def test_target_must_match_period_and_unknown_capital_stays_unknown(client):
    sales(client)
    target = upload(
        client,
        [["rep", "target"], ["مندوب تجريبي", "100"], ["TOTAL", "100"]],
        "targets",
        "2026-10-01",
        "2026-10-10",
        financial_verified=True,
    )
    accept(client, target)
    stock = upload(client, SNAPSHOT, start="2026-10-23")
    accept(client, stock)
    report = client.get(QUERY).json()
    assert report["representatives"][0]["target_achievement"]["value"] is None
    assert report["metrics"]["slow_stock_capital"]["value"] is None


@pytest.mark.parametrize("closing,expected", [("5", "50.00"), ("8", None)])
def test_sell_through_requires_cross_source_stock_and_sales_reconciliation(client, closing, expected):
    b = upload(
        client,
        [["barcode", "name", "quantity"], ["000366", "X", "10"], ["TOTAL", "", "10"]],
        start="2026-09-30",
    )
    accept(client, b)
    b = upload(
        client,
        [["barcode", "name", "quantity"], ["000366", "X", closing], ["TOTAL", "", closing]],
        start="2026-10-23",
    )
    accept(client, b)
    b = upload(
        client,
        [["barcode", "name", "sold", "returned"], ["000366", "X", "5", "0"], ["TOTAL", "", "5", "0"]],
        "sales",
        "2026-10-01",
        "2026-10-23",
    )
    accept(client, b)
    b = upload(
        client,
        [
            ["barcode", "name", "date", "kind", "incoming", "outgoing"],
            ["000366", "X", "01/10/2026", "sale", "0", "5"],
            ["TOTAL", "", "", "", "0", "5"],
        ],
        "movement",
        "2026-10-01",
        "2026-10-23",
    )
    accept(client, b)
    r = client.get(QUERY).json()
    assert r["products"][0]["sell_through"]["value"] == expected
    if expected is None:
        assert any("غير مطابق" in w for w in r["warnings"])


def movement(client, sold="3", returned="2"):
    batch = upload(
        client,
        [
            ["barcode", "name", "date", "kind", "incoming", "outgoing"],
            ["000366", "X", "01/10/2026", "sale", "0", sold],
            ["000366", "X", "02/10/2026", "sales_return", returned, "0"],
            ["TOTAL", "", "", "", returned, sold],
        ],
        "movement",
        "2026-10-01",
        "2026-10-23",
    )
    accept(client, batch)


def test_assigned_sales_scope_uses_complete_movement_and_keeps_money_scoped(client):
    sales(client, sales_coverage="assigned_only", note="Owner confirmed unassigned sales excluded")
    movement(client)
    report = client.get(QUERY).json()
    assert report["source_comparison"]["status"] == "explained_unassigned"
    assert report["source_comparison"]["unassigned_sold"] == "1"
    assert report["source_comparison"]["unassigned_returned"] == "1"
    assert report["demand_source"] == "movement"
    assert report["metrics"]["sold"]["value"] == "3.00"
    assert report["metrics"]["returned"]["value"] == "2.00"
    assert report["metrics"]["reported_net_sales"]["value"] == "135.00"
    assert report["representatives"][0]["net_sales"]["value"] == "135.00"
    assert report["products"][0]["reported_net_sales"]["value"] == "135.00"
    for field in ["net_sales", "gross_sales", "gross_profit", "cogs", "operating_profit"]:
        assert report["metrics"][field]["value"] is None
    assert report["products"][0]["net_sales"]["value"] is None
    for kind in ["csv", "xlsx", "pdf"]:
        exported = client.get(QUERY.replace("analytics", "exports/" + kind))
        assert exported.status_code == 200
        if kind == "csv":
            assert "reported_net_sales" in exported.text and "explained_unassigned" in exported.text


def test_assigned_sales_without_complete_movement_cannot_establish_full_demand(client):
    sales(client, sales_coverage="assigned_only", note="Owner confirmed subset")
    accept(client, upload(client, SNAPSHOT, start="2026-10-23", reservation_verified=True))
    report = client.get(QUERY).json()
    assert report["demand_source"] == "unreconciled"
    assert report["metrics"]["sold"]["value"] is None
    assert report["products"][0]["velocity"]["value"] is None
    assert report["products"][0]["classification"] == "insufficient_history"
    assert report["metrics"]["net_sales"]["value"] is None
    assert report["metrics"]["reported_net_sales"]["value"] == "135.00"


@pytest.mark.parametrize("assigned", [True, False])
def test_unexplained_or_negative_scope_differences_remain_blocked(client, assigned):
    sales(client, sales_coverage="assigned_only" if assigned else "store", note="Scope confirmation")
    movement(client, sold="1" if assigned else "3", returned="1")
    report = client.get(QUERY).json()
    assert report["source_comparison"]["status"] == "mismatch"
    assert report["demand_source"] == "unreconciled"
    assert report["products"][0]["classification"] == "source_conflict"
    for key in ["sold", "net_sales", "gross_profit"]:
        assert report["metrics"][key]["value"] is None
    assert report["metrics"]["reported_net_sales"]["value"] == "135.00"
