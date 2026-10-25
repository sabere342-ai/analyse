"""Private checksum-linked expectations stay outside Git; no business rows here."""

import hashlib
import json
import os
from pathlib import Path

import pytest

from madrid.contracts import ImportSpec
from madrid.ingestion import stage, transition

NAMES = {
    "snapshot": "جرد المخازن.pdf",
    "sales": "مبيعات المندوبين بالاصناف.pdf",
    "movement": "حركة تفصيلية للمخازن.pdf",
}


def source_evidence(kind):
    source = Path("samples/private") / NAMES[kind]
    if not source.exists():
        pytest.skip("Actual private POS report not supplied; no source acceptance claim")
    config = Path(os.environ.get("MADRID_PRIVATE_SPEC", "samples/private/acceptance.json"))
    if not config.exists():
        pytest.fail("Private source present: checksum-linked inspected expectations required")
    data = json.loads(config.read_text())
    evidence = next(item for item in data["reports"] if item["spec"]["report_type"] == kind)
    assert evidence["inspection_completed"] is True
    assert evidence["sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
    return source, evidence


def stage_actual(client, kind):
    source, evidence = source_evidence(kind)
    spec = ImportSpec.model_validate(evidence["spec"])
    batch = stage(
        client.app.state.factory, client.app.state.directory, source.name, source.read_bytes(), spec
    )
    return batch, evidence


@pytest.mark.parametrize("kind", ["snapshot", "sales", "movement"])
def test_actual_pos_report_full_row_and_footer_acceptance(client, kind):
    batch, evidence = stage_actual(client, kind)
    assert not batch.issues
    detail = [r for r in batch.rows if r["kind"] == "detail"]
    assert len(detail) == len(evidence["detail_rows"]) > 0
    actual = {json.dumps(r["raw"]["location"], sort_keys=True): r for r in detail}
    for expected in evidence["detail_rows"]:
        record = actual[json.dumps(expected["location"], sort_keys=True)]
        assert not record["issues"]
        for key, value in expected["data"].items():
            assert record["data"][key] == value
        assert record["data"]["barcode"].startswith("0")
        assert record["raw"]["cells"] and record["raw"]["logical_cells"]
    assert {r["raw"]["location"]["page"] for r in batch.rows} == set(range(1, evidence["pages"] + 1))
    assert all(check["matches"] for check in batch.reconciliation["checks"].values())
    for key, count in evidence["source_validation_counts"].items():
        assert batch.reconciliation["source_validation"][key] == {"checked": count, "passed": count}


def test_actual_reports_keep_discrepant_sources_separate_and_do_not_invent_profit(client):
    loaded = {}
    for kind in NAMES:
        batch, evidence = stage_actual(client, kind)
        assert not batch.issues
        with client.app.state.factory() as db:
            transition(db, batch.id, "accept", "")
        loaded[kind] = (batch, evidence)
        duplicate, _ = stage_actual(client, kind)
        assert duplicate.id == batch.id and duplicate.status == "accepted"
    spec = loaded["sales"][1]["spec"]
    query = f"start={spec['start']}&end={spec['end']}&stock_asof={loaded['snapshot'][1]['spec']['end']}"
    report = client.get("/api/analytics?" + query).json()
    assert (
        report["metrics"]["stock"]["value"] == loaded["snapshot"][1]["spec"]["expected"]["quantity"] + ".00"
    )
    assert report["metrics"]["reported_net_sales"]["value"] == spec["expected"]["net"]
    assert report["metrics"]["net_sales"]["value"] is None
    assert report["source_comparison"]["status"] == "explained_unassigned"
    assert report["demand_source"] == "movement"
    assert report["source_comparison"]["differences"]
    for key in ["cogs", "gross_profit", "operating_profit", "discounts", "sales_returns"]:
        assert report["metrics"][key]["value"] is None
    assert report["metrics"]["reported_net_discount"]["value"] == spec["expected"]["source_net_discount"]
    movement_rows = loaded["movement"][1]["detail_rows"]
    from decimal import Decimal

    sold = sum(
        (Decimal(r["data"]["outgoing"]) for r in movement_rows if r["data"]["kind"] == "sale"), Decimal(0)
    )
    returned = sum(
        (Decimal(r["data"]["incoming"]) for r in movement_rows if r["data"]["kind"] == "sales_return"),
        Decimal(0),
    )
    assert Decimal(report["metrics"]["sold"]["value"]) == sold
    assert Decimal(report["metrics"]["returned"]["value"]) == returned
    assert all(p["net_sales"]["value"] is None for p in report["products"])
    assert all(p["classification"] != "potentially_dead" for p in report["products"])
    assert all(p["classification"] != "zero_sales" for p in report["products"] if Decimal(p["sold"]) > 0)
    assert all(
        p["coverage"]["value"] is None and p["replenishment_units"] is None for p in report["products"]
    )
    assert report["snapshot_date"] != report["period"]["end"]
    assert len(client.get("/api/batches").json()) == len(NAMES)
    # The actual full stock report must export within the unchanged renderer limits.
    response = client.get("/api/exports/pdf?" + query)
    assert response.status_code == 200, response.text
    import io

    import pdfplumber

    with pdfplumber.open(io.BytesIO(response.content)) as exported:
        assert len(exported.pages) < 50
        text = "\n".join(page.extract_text() or "" for page in exported.pages)
        assert all(row["data"]["barcode"] in text for row in loaded["snapshot"][1]["detail_rows"])


def test_actual_profile_rejects_wrong_period_metadata(client):
    source, evidence = source_evidence("snapshot")
    spec = ImportSpec.model_validate({**evidence["spec"], "start": "2001-01-01", "end": "2001-01-01"})
    with pytest.raises(ValueError, match="source_period_does_not_match_import_metadata"):
        stage(client.app.state.factory, client.app.state.directory, source.name, source.read_bytes(), spec)


@pytest.mark.parametrize("kind", ["snapshot", "sales"])
def test_actual_source_dates_can_be_read_without_changing_source_facts(client, kind):
    source, evidence = source_evidence(kind)
    spec = ImportSpec.model_validate(
        {**evidence["spec"], "start": "2001-01-01", "end": "2001-01-01", "source_dates": "report"}
    )
    batch = stage(
        client.app.state.factory, client.app.state.directory, source.name, source.read_bytes(), spec
    )
    assert not batch.issues
    assert batch.start == evidence["spec"]["start"] and batch.end == evidence["spec"]["end"]
    assert len([r for r in batch.rows if r["kind"] == "detail"]) == len(evidence["detail_rows"])
    again = stage(
        client.app.state.factory,
        client.app.state.directory,
        source.name,
        source.read_bytes(),
        spec.model_copy(update={"start": spec.start.replace(year=2002), "end": spec.end.replace(year=2002)}),
    )
    assert again.id == batch.id
