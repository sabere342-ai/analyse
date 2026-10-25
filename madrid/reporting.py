from __future__ import annotations

import csv
import html
import io
import json
import subprocess
import sys
import unicodedata
from pathlib import Path
from typing import Any

from openpyxl import Workbook

from madrid.contracts import decimal_value

PDF_LABELS = {
    "reported_net_sales": "صافي قيمة تقرير المبيعات المنسوبة",
    "reported_net_discount": "صافي خصم تقرير المبيعات المنسوبة",
    "net_discount": "صافي الخصم بعد عكس خصم المرتجعات",
    "snapshot_date": "تاريخ رصيد المخزون",
    "source_comparison": "مقارنة مصادر البيع",
    "source_conflict": "تعارض بين مصادر المبيعات",
    "period": "الفترة",
    "end": "نهاية الفترة",
    "summary": "ملخص المحل",
    "inventory": "المخزون",
    "representatives": "المندوبين",
    "recommendations": "توصيات",
    "warning": "ملاحظة",
    "gross_sales": "إجمالي المبيعات",
    "discounts": "الخصومات",
    "sales_returns": "قيمة المرتجعات",
    "net_sales": "صافي المبيعات",
    "cogs": "تكلفة البضاعة المباعة",
    "gross_profit": "مجمل الربح",
    "gross_margin": "هامش الربح ٪",
    "expenses": "المصروفات",
    "operating_profit": "الربح التشغيلي",
    "sold": "الوحدات المباعة",
    "returned": "الوحدات المرتجعة",
    "stock": "رصيد المخزون",
    "inventory_cost_value": "قيمة المخزون بالتكلفة",
    "slow_stock_capital": "رأس المال في المخزون البطيء",
    "available": "المتاح",
    "net_units": "صافي الوحدات",
    "velocity": "صافي قطعة / يوم",
    "coverage": "التغطية بالأيام",
    "sell_through": "معدل التصريف ٪",
    "replenishment_units": "كمية مراجعة التوريد",
    "classification": "تصنيف الحركة",
    "insufficient_history": "تاريخ غير كافٍ",
    "zero_sales": "بلا مبيعات في الفترة",
    "slow": "بطيء الحركة",
    "potentially_dead": "ركود محتمل",
    "discount": "قيمة الخصم",
    "discount_rate": "معدل الخصم ٪",
    "return_rate": "معدل المرتجعات ٪",
    "target_achievement": "تحقيق الهدف ٪",
    "profit_contribution": "المساهمة في الربح",
}


def safe_text(value: object) -> str:
    text = "" if value is None else str(value)
    probe = text
    while probe and (probe[0].isspace() or unicodedata.category(probe[0]) in {"Cc", "Cf"}):
        probe = probe[1:]
    if probe.startswith(("=", "+", "-", "@")) or text.startswith(("\t", "\r", "\n")):
        return "'" + text
    return text


def report_rows(report: dict[str, Any]) -> list[list[str]]:
    rows = [["section", "subject", "barcode", "metric", "value", "status", "evidence"]]
    rows.append(
        ["period", report["period"]["start"], "", "end", report["period"]["end"], report["currency"], ""]
    )
    if report.get("snapshot_date"):
        rows.append(["period", "المخزون", "", "snapshot_date", report["snapshot_date"], "available", ""])
    comparison = report.get("source_comparison", {})
    if comparison.get("status") in {"matched", "mismatch", "explained_unassigned"}:
        rows.append(
            [
                "source_comparison",
                "تقرير المبيعات",
                "",
                "sold",
                comparison["reported_sold"],
                comparison["status"],
                "",
            ]
        )
        rows.append(
            [
                "source_comparison",
                "حركة المخزون",
                "",
                "sold",
                comparison["movement_sold"],
                comparison["status"],
                "",
            ]
        )
        rows.append(
            [
                "source_comparison",
                "تقرير المبيعات",
                "",
                "returned",
                comparison["reported_returned"],
                comparison["status"],
                "",
            ]
        )
        rows.append(
            [
                "source_comparison",
                "حركة المخزون",
                "",
                "returned",
                comparison["movement_returned"],
                comparison["status"],
                "",
            ]
        )
    if comparison.get("status") == "explained_unassigned":
        for field in ["sold", "returned"]:
            rows.append(
                [
                    "source_comparison",
                    "بدون مندوب — فرق وحدات مؤكد",
                    "",
                    field,
                    comparison["unassigned_" + field],
                    "explained_unassigned",
                    "owner_confirmed_unassigned_sales",
                ]
            )
    for key, metric in report["metrics"].items():
        rows.append(
            ["summary", "المحل", "", key, metric["value"] or "", metric["status"], metric.get("reason") or ""]
        )
    for p in report["products"]:
        for field in [
            "stock",
            "available",
            "sold",
            "returned",
            "net_units",
            "velocity",
            "coverage",
            "sell_through",
            "net_sales",
            "replenishment_units",
            "classification",
            *(["reported_net_sales"] if "reported_net_sales" in report["metrics"] else []),
        ]:
            value = p.get(field)
            status = "available" if value is not None else "unavailable"
            if isinstance(value, dict):
                status, value = value["status"], value["value"]
            rows.append(
                [
                    "inventory",
                    p["name"],
                    p["barcode"],
                    field,
                    str(value) if value is not None else "",
                    status,
                    json.dumps(p["evidence"], ensure_ascii=False),
                ]
            )
    for rep in report["representatives"]:
        for field, value in rep.items():
            if isinstance(value, dict) and "status" in value:
                rows.append(
                    ["representatives", rep["rep"], "", field, value["value"] or "", value["status"], ""]
                )
    for rec in report["recommendations"]:
        rows.append(
            [
                "recommendations",
                rec["subject"],
                rec["barcode"],
                rec["observation"],
                rec["action"],
                rec["quality"],
                json.dumps(rec["evidence"], ensure_ascii=False),
            ]
        )
    for warning in report["warnings"]:
        rows.append(["warning", warning, "", "", "", "limited", ""])
    return rows


def export_report(report: dict[str, Any], kind: str) -> bytes:
    if kind == "pdf" and __name__ != "__main__":
        try:
            worker = subprocess.run(
                [sys.executable, "-m", "madrid.reporting"],
                input=json.dumps(report, ensure_ascii=False).encode(),
                capture_output=True,
                timeout=45,
            )
        except subprocess.TimeoutExpired as exc:
            raise ValueError("pdf_render_timeout") from exc
        if worker.returncode or not worker.stdout.startswith(b"%PDF-"):
            raise ValueError("pdf_render_failed_or_resource_limit")
        return worker.stdout
    rows = report_rows(report)
    if kind == "csv":
        output = io.StringIO(newline="")
        writer = csv.writer(output)
        for row in rows:
            escaped = [safe_text(c) for c in row]
            if (
                row[0] in {"summary", "inventory", "representatives"}
                and row[3] != "classification"
                and row[4]
            ):
                try:
                    decimal_value(row[4])
                    escaped[4] = row[
                        4
                    ]  # Trusted validated numeric measures keep their negative signs exactly.
                except ValueError:
                    pass
            writer.writerow(escaped)
        return output.getvalue().encode("utf-8-sig")
    if kind == "xlsx":
        book = Workbook()
        sheet = book.active
        assert sheet is not None
        sheet.title = "Analytics"
        sheet.sheet_view.rightToLeft = True
        for row in rows:
            sheet.append(row)
            for cell in sheet[sheet.max_row]:
                cell.data_type = "s"
                cell.number_format = "@"
        sheet.freeze_panes = "A2"
        sheet.auto_filter.ref = sheet.dimensions
        for column in ["A", "B", "C", "D", "E", "F", "G"]:
            sheet.column_dimensions[column].width = 25 if column != "G" else 55
        stream = io.BytesIO()
        book.save(stream)
        return stream.getvalue()
    if kind != "pdf":
        raise ValueError("unsupported_export")
    if len(rows) > 12000:
        raise ValueError("pdf_export_too_large_narrow_period")
    from weasyprint import HTML, Attachment

    def deny_fetch(url: str, *args: Any, **kwargs: Any) -> Any:
        raise ValueError("external_and_local_fetch_prohibited")

    title = f"تقرير مدريد | {report['currency']}"
    headers = ["القسم", "الموضوع", "الباركود", "المؤشر", "القيمة", "الحالة"]
    display_rows = []
    statuses = {
        "available": "متاح",
        "unavailable": "غير متاح",
        "limited": "بيانات محدودة",
        "matched": "مطابق",
        "mismatch": "غير مطابق",
        "explained_unassigned": "فرق نطاق مؤكد",
    }
    for row in rows[1:]:
        if row[0] in {"inventory", "representatives"}:
            continue  # A full-size stock report needs one product per row, not eleven repeated rows.
        values = row[:6].copy()
        values[0] = PDF_LABELS.get(values[0], values[0])
        values[3] = PDF_LABELS.get(values[3], values[3])
        values[5] = statuses.get(values[5], "راجع جودة الدليل" if row[0] == "recommendations" else values[5])
        if row[3] == "classification":
            values[4] = PDF_LABELS.get(values[4], values[4])
        display_rows.append(values)
    table = "".join(
        "<tr>" + "".join("<td>" + html.escape(str(c)) + "</td>" for c in row[:6]) + "</tr>"
        for row in display_rows
    )

    def value(item: Any) -> str:
        if isinstance(item, dict):
            item = item.get("value")
        return "غير متاح" if item is None else str(item)

    def compact_table(title: str, headings: list[str], body: list[list[str]], numeric: set[int]) -> str:
        if not body:
            return ""
        header = "".join("<th>" + html.escape(h) + "</th>" for h in headings)
        lines = []
        for cells in body:
            lines.append(
                "<tr>"
                + "".join(
                    '<td class="'
                    + ("num" if i in numeric else "")
                    + '">'
                    + html.escape(c).replace("\n", "<br>")
                    + "</td>"
                    for i, c in enumerate(cells)
                )
                + "</tr>"
            )
        return (
            "<h2>"
            + html.escape(title)
            + '</h2><table class="compact"><thead><tr>'
            + header
            + "</tr></thead><tbody>"
            + "".join(lines)
            + "</tbody></table>"
        )

    partial_values = "reported_net_sales" in report["metrics"]
    inventory = compact_table(
        "المنتجات والمخزون — كل منتج مرة واحدة",
        [
            "الباركود",
            "المنتج / التصنيف",
            "الرصيد / المتاح",
            "مباع / مرتجع",
            "صافي الوحدات",
            "صافي قيمة التقرير المنسوب" if partial_values else "صافي المبيعات",
            "قطعة/يوم — تغطية يوم",
            "حالة البيانات",
        ],
        [
            [
                p["barcode"],
                p["name"] + "\n" + p["category"],
                value(p["stock"]) + " / " + value(p["available"]),
                value(p["sold"]) + " / " + value(p["returned"]),
                value(p["net_units"]),
                value(p.get("reported_net_sales") if partial_values else p["net_sales"]),
                value(p["velocity"]) + " — " + value(p["coverage"]),
                PDF_LABELS.get(p["classification"], p["classification"]),
            ]
            for p in report["products"]
        ],
        {0, 2, 3, 4, 5, 6},
    )
    representatives = compact_table(
        "أداء المندوبين حسب تقرير المبيعات",
        [
            "المندوب",
            "الترتيب",
            "صافي المبيعات",
            "مباع / مرتجع",
            "مرتجعات ٪",
            "صافي الخصم بعد المرتجعات",
            "خصم مبيعات ٪",
            "تحقيق الهدف ٪",
            "المساهمة في الربح",
        ],
        [
            [
                r["rep"],
                value(r["rank"]),
                value(r["net_sales"]),
                value(r["sold"]) + " / " + value(r["returned"]),
                value(r["return_rate"]),
                value(r.get("net_discount")),
                value(r["discount_rate"]),
                value(r["target_achievement"]),
                value(r["profit_contribution"]),
            ]
            for r in report["representatives"]
        ],
        set(range(1, 9)),
    )
    document = (
        """<!doctype html><html lang="ar" dir="rtl"><meta charset="utf-8"><style>
    @page {size:A4 landscape; margin:15mm; @bottom-center {font-family:'DejaVu Sans';font-size:9px;direction:ltr; content:counter(page) " / " counter(pages)}}
    body{font-family:'DejaVu Sans',sans-serif;font-size:10px;color:#163c32}
    h1{font-size:18px}table{width:100%;border-collapse:collapse}thead{display:table-header-group}
    td,th{padding:6px;border:1px solid #ddd;text-align:right;overflow-wrap:anywhere}tr{break-inside:avoid}
    th{background:#e9f1ed}td:nth-child(3),td:nth-child(5){direction:ltr;unicode-bidi:isolate}
    h2{font-size:14px;margin-top:22px;break-after:avoid}.compact{font-size:9px}.compact td,.compact th{padding:5px}.num{direction:ltr;unicode-bidi:isolate}
    .summary th:nth-child(3){width:75px;white-space:nowrap}
    </style><h1>"""
        + html.escape(title)
        + '</h1><p>الفترة: <bdi dir="ltr">'
        + html.escape(report["period"]["start"])
        + '</bdi> إلى <bdi dir="ltr">'
        + html.escape(report["period"]["end"])
        + "</bdi></p>"
        + '<p>المؤشرات غير المتاحة ليست صفرًا. التفاصيل والأدلة الكاملة في تصدير XLSX.</p><table class="summary"><thead><tr>'
        + "".join("<th>" + h + "</th>" for h in headers)
        + "</tr></thead><tbody>"
        + table
        + "</tbody></table>"
        + inventory
        + representatives
        + "</html>"
    )
    license_text = Path(__file__).with_name("font-license.txt").read_text(encoding="utf-8")
    return HTML(string=document, url_fetcher=deny_fetch).write_pdf(
        full_fonts=True,
        attachments=[
            Attachment(
                string=license_text, name="DejaVu-font-license.txt", description="Embedded font license"
            )
        ],
    )


if __name__ == "__main__":
    from madrid.worker_limits import limit_worker

    limit_worker(35)
    sys.stdout.buffer.write(export_report(json.load(sys.stdin.buffer), "pdf"))
