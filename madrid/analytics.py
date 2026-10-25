from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal
from typing import Any

from madrid.contracts import Rules, decimal_value
from madrid.db import Batch

ZERO = Decimal(0)


def amount(value: Decimal | None, reason: str = "missing_verified_data") -> dict[str, Any]:
    return {
        "value": str(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)) if value is not None else None,
        "status": "available" if value is not None else "unavailable",
        "reason": None if value is not None else reason,
    }


def cover(batches: list[Batch], start: str, end: str) -> bool:
    cursor = date.fromisoformat(start)
    for batch in sorted(batches, key=lambda b: b.start):
        if date.fromisoformat(batch.start) > cursor:
            return False
        cursor = max(cursor, date.fromisoformat(batch.end) + timedelta(days=1))
    return cursor > date.fromisoformat(end)


def calculate(
    batches: list[Batch], start: str, end: str, scope: str, rules: Rules, stock_asof: str | None = None
) -> dict[str, Any]:
    active = [b for b in batches if b.status == "accepted" and b.scope == scope]
    period = [b for b in active if b.start >= start and b.end <= end]
    sales_batches = [b for b in period if b.report_type == "sales"]
    sales_complete = cover(sales_batches, start, end)
    expense_batches = [b for b in period if b.report_type == "expenses"]
    expenses_complete = cover(expense_batches, start, end)
    snapshots = [b for b in active if b.report_type == "snapshot" and b.end <= (stock_asof or end)]
    snapshot = max(snapshots, key=lambda b: b.end) if snapshots else None
    currency_set = {
        b.metadata_json["currency"] for b in period if b.report_type in {"sales", "expenses", "targets"}
    }
    if snapshot:
        currency_set.add(snapshot.metadata_json["currency"])
    currencies_match = len(currency_set) <= 1
    days = Decimal((date.fromisoformat(end) - date.fromisoformat(start)).days + 1)
    products: dict[str, dict[str, Any]] = {}
    sales: list[dict[str, Any]] = []
    expenses: list[dict[str, Any]] = []
    movements: list[dict[str, Any]] = []
    targets: dict[str, Decimal] = {}

    def details(batch: Batch) -> list[dict[str, Any]]:
        return [
            {
                **r["data"],
                "evidence": {
                    "batch_id": batch.id,
                    "occurrence": r["occurrence"],
                    "location": r["raw"]["location"],
                },
            }
            for r in batch.rows
            if r["kind"] == "detail"
        ]

    def product(row: dict[str, Any]) -> dict[str, Any]:
        code = row["barcode"]
        if code not in products:
            products[code] = {
                "barcode": code,
                "name": row.get("name", code),
                "category": row.get("category") or "غير مصنف",
                "sales": [],
                "stock": None,
                "available": None,
                "evidence": [],
                "introduced": None,
            }
        p = products[code]
        p["evidence"].append(row["evidence"])
        return p

    for batch in period:
        rows = details(batch)
        if batch.report_type == "sales":
            sales.extend(rows)
            for row in rows:
                product(row)["sales"].append(row)
        elif batch.report_type == "expenses":
            expenses.extend(rows)
        elif batch.report_type == "movement":
            movements.extend(rows)
            for row in rows:
                product(row)
        elif batch.report_type == "targets" and batch.start == start and batch.end == end:
            for row in rows:
                targets[row["rep"]] = targets.get(row["rep"], ZERO) + decimal_value(row["target"])
    if snapshot:
        for row in details(snapshot):
            p = product(row)
            p.update(
                {
                    "name": row.get("name", p["name"]),
                    "category": row.get("category") or p["category"],
                    "stock": row["quantity"],
                    "available": row.get("available"),
                    "introduced": row.get("introduced"),
                }
            )

    def sum_field(rows: list[dict[str, Any]], field: str, complete: bool = True) -> Decimal | None:
        if not complete or any(field not in r for r in rows):
            return None
        return sum((decimal_value(r[field]) for r in rows), ZERO)

    financial_complete = sales_complete and currencies_match
    reported_financial_complete = financial_complete
    assigned_only = any(b.metadata_json.get("sales_coverage") == "assigned_only" for b in sales_batches)
    net = sum_field(sales, "net", financial_complete)
    gross = sum_field(sales, "gross", financial_complete)
    discounts = sum_field(sales, "discount", financial_complete)
    net_discount = sum_field(sales, "source_net_discount", financial_complete)
    reported_net, reported_net_discount = net, net_discount
    credits = sum_field(sales, "return_value", financial_complete)
    cogs = sum_field(sales, "cogs", financial_complete)
    gross_profit = net - cogs if net is not None and cogs is not None else None
    expense = sum_field(expenses, "amount", expenses_complete and currencies_match)
    operating = gross_profit - expense if gross_profit is not None and expense is not None else None
    result_products = []
    recommendations = []
    cross_warnings: list[str] = []
    movement_complete = cover([b for b in period if b.report_type == "movement"], start, end)
    comparison: dict[str, Any] = {"status": "not_available", "differences": []}
    demand_complete = sales_complete and not assigned_only
    motion_sales: dict[str, list[Decimal]] = defaultdict(lambda: [ZERO, ZERO])
    for row in movements:
        if row["kind"] == "sale":
            motion_sales[row["barcode"]][0] += decimal_value(row["outgoing"])
        elif row["kind"] == "sales_return":
            motion_sales[row["barcode"]][1] += decimal_value(row["incoming"])
    if movement_complete and sales_complete:
        for code in sorted(set(products) | set(motion_sales)):
            report_rows = products.get(code, {}).get("sales", [])
            reported = [sum((decimal_value(r[f]) for r in report_rows), ZERO) for f in ["sold", "returned"]]
            observed = motion_sales[code]
            if reported != observed:
                comparison["differences"].append(
                    {
                        "barcode": code,
                        "reported_sold": str(reported[0]),
                        "reported_returned": str(reported[1]),
                        "movement_sold": str(observed[0]),
                        "movement_returned": str(observed[1]),
                        "evidence": products.get(code, {}).get("evidence", []),
                    }
                )
        comparison.update(
            {
                "status": "mismatch" if comparison["differences"] else "matched",
                "reported_sold": str(sum_field(sales, "sold")),
                "reported_returned": str(sum_field(sales, "returned")),
                "movement_sold": str(sum((v[0] for v in motion_sales.values()), ZERO)),
                "movement_returned": str(sum((v[1] for v in motion_sales.values()), ZERO)),
            }
        )
        if comparison["differences"]:
            demand_complete = False
            subset_valid = all(
                decimal_value(d["movement_sold"]) >= decimal_value(d["reported_sold"])
                and decimal_value(d["movement_returned"]) >= decimal_value(d["reported_returned"])
                for d in comparison["differences"]
            )
            if assigned_only and subset_valid:
                comparison.update(
                    {
                        "status": "explained_unassigned",
                        "explanation": "owner_confirmed_unassigned_sales",
                        "unassigned_sold": str(
                            decimal_value(comparison["movement_sold"])
                            - decimal_value(comparison["reported_sold"])
                        ),
                        "unassigned_returned": str(
                            decimal_value(comparison["movement_returned"])
                            - decimal_value(comparison["reported_returned"])
                        ),
                    }
                )
            else:
                cross_warnings.append(
                    "مصدر المبيعات وحركات البيع بهما فروق غير مفسرة؛ لا يتم اعتبار أي منهما إجماليًا متوافقًا للمحل أو استنتاج الطلب من بيانات متناقضة"
                )
    use_movement = assigned_only and movement_complete and comparison["status"] != "mismatch"
    if use_movement:
        demand_complete = True
    if assigned_only:
        cross_warnings.append(
            "تقرير المندوبين للمبيعات المنسوبة فقط حسب تأكيد صاحب المحل؛ الوحدات من الحركة عند اكتمالها، وقيم المبيعات بدون مندوب غير متاحة ولا يتم تقديرها"
        )
    if assigned_only or comparison["status"] == "mismatch":
        financial_complete = False
        net = gross = discounts = net_discount = credits = cogs = gross_profit = operating = None
    latest_cost: dict[str, tuple[str, str, str]] = {}
    for batch in sorted(active, key=lambda b: b.end):
        if batch.report_type == "costs" and snapshot and batch.end <= snapshot.end:
            for row in details(batch):
                latest_cost[row["barcode"]] = (row["cost"], batch.id, batch.metadata_json["currency"])

    def recommend(p: dict[str, Any], observation: str, action: str, impact: str, quality: str) -> None:
        recommendations.append(
            {
                "subject": p["name"],
                "barcode": p["barcode"],
                "observation": observation,
                "evidence": p["evidence"],
                "impact": impact,
                "action": action,
                "quality": quality,
                "period": {"start": start, "end": end},
                "rules": rules.model_dump(),
            }
        )

    valuation = ZERO
    valued = 0
    slow_capital = ZERO
    slow_cost_complete = True
    for p in products.values():
        rows = p["sales"]
        sold = motion_sales[p["barcode"]][0] if use_movement else sum_field(rows, "sold", demand_complete)
        returned = (
            motion_sales[p["barcode"]][1] if use_movement else sum_field(rows, "returned", demand_complete)
        )
        if use_movement and not any(r["barcode"] == p["barcode"] for r in movements):
            p["evidence"].extend(
                {"batch_id": b.id, "kind": "coverage", "period": {"start": b.start, "end": b.end}}
                for b in period
                if b.report_type == "movement"
            )
        q = sold - returned if sold is not None and returned is not None else None
        velocity = q / days if q is not None and demand_complete else None
        available = decimal_value(p["available"]) if p["available"] is not None else None
        stock = decimal_value(p["stock"]) if p["stock"] is not None else None
        aligned = bool(snapshot and snapshot.end == end)
        coverage = (
            available / velocity
            if available is not None and available >= 0 and velocity and velocity > 0 and aligned
            else None
        )
        age = (
            (date.fromisoformat(end) - date.fromisoformat(p["introduced"])).days + 1
            if p["introduced"]
            else None
        )
        availability = None
        if (
            rows
            and all("in_stock_days" in row for row in rows)
            and all(b.metadata_json.get("availability_verified") for b in sales_batches)
        ):
            # One availability value per product per report is required; duplicated rep values cannot be summed.
            if len(rows) == 1:
                availability = decimal_value(rows[0]["in_stock_days"])
        adjusted = (
            sold / availability if sold is not None and availability and 0 < availability <= days else None
        )
        classification = "insufficient_history"
        eligible = (
            demand_complete
            and age is not None
            and age >= rules.min_history_days
            and days >= rules.min_history_days
        )
        if stock is not None and stock > 0 and sold == 0 and demand_complete:
            classification = "zero_sales"
            recommend(
                p,
                "مخزون موجب بلا مبيعات في الفترة المكتملة",
                "راجع عرض المنتج والطلب عليه",
                "رأس مال محتمل غير متحرك؛ عمر المنتج وتوافره يحتاجان تحقق",
                "limited_history",
            )
            if (
                eligible
                and days >= rules.dead_no_sale_days
                and age is not None
                and age >= rules.dead_no_sale_days
                and availability == days
            ):
                classification = "potentially_dead"
        elif (
            eligible
            and stock is not None
            and stock > 0
            and velocity is not None
            and 0 <= velocity < decimal_value(rules.slow_velocity)
            and availability == days
        ):
            classification = "slow"
        if coverage is not None and coverage > rules.max_cover_days:
            recommend(
                p,
                f"تغطية المخزون {coverage.quantize(Decimal('0.1'))} يوم",
                "راجع خطة الشراء",
                "مخزون أعلى من حد التغطية المحدد",
                "verified_window_with_seasonality_limits",
            )
        needed = None
        if aligned and available is not None and available >= 0 and velocity is not None and velocity > 0:
            needed = max(
                ZERO,
                velocity * (rules.lead_time_days + rules.target_cover_days)
                + decimal_value(rules.safety_units)
                - available,
            ).to_integral_value(rounding=ROUND_CEILING)
            if coverage is not None and coverage <= rules.lead_time_days and needed > 0:
                recommend(
                    p,
                    f"تغطية {coverage.quantize(Decimal('0.1'))} يوم فقط",
                    "راجع إعادة التوريد",
                    f"كمية مراجعة تقديرية {needed}؛ ليست أمر شراء",
                    "verified_window_with_seasonality_limits",
                )
        if (
            sold
            and sold > 0
            and returned is not None
            and returned / sold * 100 >= decimal_value(rules.return_alert_rate)
        ):
            recommend(
                p,
                "نسبة المرتجعات أعلى من الحد المضبوط",
                "افحص أسباب المرتجعات",
                "قد تتأثر الإيرادات والطلب؛ النسبة ليست تقييمًا للموظف",
                "same_period_activity",
            )
        cost = latest_cost.get(p["barcode"])
        cost_usable = bool(cost and snapshot and cost[2] == snapshot.metadata_json["currency"])
        if stock is not None and cost and cost_usable:
            valuation += stock * decimal_value(cost[0])
            valued += 1
        if classification in {"slow", "potentially_dead"}:
            if stock is not None and cost and cost_usable:
                slow_capital += stock * decimal_value(cost[0])
            else:
                slow_cost_complete = False
        elif (
            stock is not None and stock > 0 and (not eligible or availability != days or not demand_complete)
        ):
            slow_cost_complete = False
        if not demand_complete and comparison["status"] == "mismatch":
            classification = "source_conflict"
        # Sell-through needs an actual opening snapshot and full reconciled external receipts.
        opening = [
            b
            for b in active
            if b.report_type == "snapshot"
            and b.end == (date.fromisoformat(start) - timedelta(days=1)).isoformat()
        ]
        movement_batches = [b for b in period if b.report_type == "movement"]
        sell_through = None
        if (
            opening
            and aligned
            and scope == "store"
            and demand_complete
            and cover(movement_batches, start, end)
            and q is not None
        ):
            opening_rows = [r for r in details(opening[0]) if r["barcode"] == p["barcode"]]
            pr_moves = [r for r in movements if r["barcode"] == p["barcode"]]
            if opening_rows and not any(
                r["kind"] in {"adjustment_in", "adjustment_out", "purchase_return"} for r in pr_moves
            ):
                base = decimal_value(opening_rows[0]["quantity"]) + sum(
                    (decimal_value(r["incoming"]) for r in pr_moves if r["kind"] == "purchase"), ZERO
                )
                movement_net_sales = sum(
                    (decimal_value(r["outgoing"]) for r in pr_moves if r["kind"] == "sale"), ZERO
                ) - sum((decimal_value(r["incoming"]) for r in pr_moves if r["kind"] == "sales_return"), ZERO)
                closing = decimal_value(opening_rows[0]["quantity"]) + sum(
                    (decimal_value(r["incoming"]) - decimal_value(r["outgoing"]) for r in pr_moves), ZERO
                )
                reconciled = closing == stock and movement_net_sales == q
                if not reconciled:
                    cross_warnings.append(
                        f"المخزون أو صافي حركة البيع غير مطابق للمصادر الأخرى للمنتج {p['barcode']}؛ Sell-through غير معتمد"
                    )
                if base > 0 and reconciled:
                    sell_through = q / base * 100
        result_products.append(
            {k: v for k, v in p.items() if k not in {"sales"}}
            | {
                "sold": str(sold) if sold is not None else None,
                "returned": str(returned) if returned is not None else None,
                "net_units": str(q) if q is not None else None,
                "velocity": amount(velocity),
                "coverage": amount(coverage, "requires_positive_demand_available_stock_and_aligned_snapshot"),
                "availability_adjusted_velocity": amount(adjusted, "verified_in_stock_days_required"),
                "sell_through": amount(sell_through, "verified_opening_supply_basis_required"),
                "replenishment_units": str(needed) if needed is not None else None,
                "classification": classification,
                "net_sales": amount(
                    sum_field(rows, "net", financial_complete and (bool(rows) or demand_complete))
                ),
                "reported_net_sales": amount(sum_field(rows, "net", reported_financial_complete)),
            }
        )

    reps: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in sales:
        reps[row.get("rep") or "غير منسوب"].append(row)
    rep_result: list[dict[str, Any]] = []
    for rep, rows in reps.items():
        rnet = sum_field(rows, "net", reported_financial_complete)
        rgross = sum_field(rows, "gross", reported_financial_complete)
        rdiscount = sum_field(rows, "discount", reported_financial_complete)
        rsold = sum_field(rows, "sold", sales_complete)
        rreturned = sum_field(rows, "returned", sales_complete)
        rcogs = sum_field(rows, "cogs", reported_financial_complete)
        target = targets.get(rep)
        rep_result.append(
            {
                "rep": rep,
                "net_sales": amount(rnet),
                "gross_sales": amount(rgross),
                "discount": amount(rdiscount),
                "net_discount": amount(sum_field(rows, "source_net_discount", reported_financial_complete)),
                "discount_rate": amount(
                    rdiscount / rgross * 100 if rdiscount is not None and rgross and rgross > 0 else None
                ),
                "sold": amount(rsold),
                "returned": amount(rreturned),
                "return_rate": amount(
                    rreturned / rsold * 100 if rreturned is not None and rsold and rsold > 0 else None
                ),
                "target_achievement": amount(
                    rnet / target * 100 if rnet is not None and target and target > 0 else None
                ),
                "profit_contribution": amount(
                    rnet - rcogs if rnet is not None and rcogs is not None else None
                ),
                "products": [
                    {
                        "barcode": code,
                        "contribution": amount(
                            sum((decimal_value(r["net"]) for r in rows if r["barcode"] == code), ZERO)
                            / rnet
                            * 100
                            if rnet and rnet > 0 and all("net" in r for r in rows)
                            else None
                        ),
                    }
                    for code in sorted({r["barcode"] for r in rows})
                ],
            }
        )
    rep_result.sort(
        key=lambda r: (
            -(decimal_value(r["net_sales"]["value"]) if r["net_sales"]["value"] else Decimal("-1e20")),
            r["rep"],
        )
    )
    for i, rep_row in enumerate(rep_result):
        rep_row["rank"] = (
            (
                rep_result[i - 1]["rank"]
                if i and rep_row["net_sales"]["value"] == rep_result[i - 1]["net_sales"]["value"]
                else i + 1
            )
            if rep_row["net_sales"]["value"] is not None
            else None
        )
    categories: dict[str, dict[str, Any]] = {}
    for p in result_products:
        c = categories.setdefault(
            p["category"],
            {
                "category": p["category"],
                "stock": ZERO,
                "net_units": ZERO,
                "net_sales": ZERO,
                "incoming": ZERO,
                "outgoing": ZERO,
            },
        )
        c["stock"] += decimal_value(p["stock"]) if p["stock"] is not None else ZERO
        c["net_units"] += decimal_value(p["net_units"]) if p["net_units"] is not None else ZERO
        raw_product_net = sum_field(products[p["barcode"]]["sales"], "net", financial_complete)
        c["net_sales"] += raw_product_net if raw_product_net is not None else ZERO
    for r in movements:
        category = products.get(r["barcode"], {}).get("category", r.get("category") or "غير مصنف")
        c = categories.setdefault(
            category,
            {
                "category": category,
                "stock": ZERO,
                "net_units": ZERO,
                "net_sales": ZERO,
                "incoming": ZERO,
                "outgoing": ZERO,
            },
        )
        c["incoming"] += decimal_value(r["incoming"])
        c["outgoing"] += decimal_value(r["outgoing"])
    categories_with_sales = {products[r["barcode"]]["category"] for r in sales}
    category_result = [
        {
            "category": c["category"],
            "stock": str(c["stock"]) if snapshot else None,
            "net_units": str(c["net_units"]) if demand_complete else None,
            "net_sales": amount(
                c["net_sales"]
                if net is not None and (demand_complete or c["category"] in categories_with_sales)
                else None
            ),
            "contribution": amount(
                c["net_sales"] / net * 100
                if net and net > 0 and (demand_complete or c["category"] in categories_with_sales)
                else None
            ),
            "incoming": str(c["incoming"]) if movement_complete else None,
            "outgoing": str(c["outgoing"]) if movement_complete else None,
        }
        for c in categories.values()
    ]
    result_products.sort(
        key=lambda p: (-(decimal_value(p["net_units"]) if p["net_units"] is not None else ZERO), p["barcode"])
    )
    warnings = cross_warnings
    if not sales_complete:
        warnings.append("فترة المبيعات غير مكتملة؛ المؤشرات الكلية وصفر المبيعات غير معتمدين")
    if any(
        b.report_type == "sales" and b.start <= end and b.end >= start and b not in period for b in active
    ):
        warnings.append("تقارير مجمعة تتقاطع جزئيًا مع الفترة مستبعدة؛ لا يتم توزيعها على أيام بالتخمين")
    if not currencies_match:
        warnings.append("عملات مختلفة؛ المؤشرات المالية غير متاحة")
    if snapshot and snapshot.end != end:
        warnings.append("تاريخ الجرد مختلف عن نهاية فترة المبيعات؛ التغطية وإعادة التوريد غير متاحتين")
    finance_evidence = [r["evidence"] for r in sales + expenses]

    def financial_recommendation(observation: str, action: str, impact: str) -> None:
        recommendations.append(
            {
                "subject": "أداء المحل",
                "barcode": "",
                "observation": observation,
                "action": action,
                "impact": impact,
                "quality": "verified_financial_inputs",
                "evidence": finance_evidence,
                "period": {"start": start, "end": end},
                "rules": rules.model_dump(),
            }
        )

    if operating is not None and operating < 0:
        financial_recommendation(
            "الربح التشغيلي سالب في الفترة",
            "راجع المصروفات وتكلفة البيع",
            "المصروفات وتكلفة البضاعة أعلى من صافي المبيعات المتحقق",
        )
    if (
        gross_profit is not None
        and net is not None
        and net > 0
        and gross_profit / net * 100 < decimal_value(rules.minimum_margin_rate)
    ):
        financial_recommendation(
            "هامش الربح أقل من الحد المضبوط",
            "راجع الأسعار والتكاليف والخصومات",
            "الهامش المتحقق أقل من الحد؛ لا توجد نسبة خصم مقترحة تلقائيًا",
        )
    if (
        discounts is not None
        and gross is not None
        and gross > 0
        and discounts / gross * 100 >= decimal_value(rules.discount_alert_rate)
    ):
        financial_recommendation(
            "نسبة الخصومات أعلى من الحد المضبوط",
            "راجع استراتيجية الخصومات",
            "راجع أثر الخصم على الإيرادات والهامش مع بيانات التكلفة",
        )
    return {
        "period": {"start": start, "end": end, "scope": scope, "stock_asof": stock_asof or end},
        "currency": next(iter(currency_set), "EGP"),
        "sales_complete": sales_complete,
        "sales_coverage": "assigned_only" if assigned_only else "store",
        "demand_source": "movement"
        if use_movement
        else "sales_report"
        if demand_complete
        else "unreconciled",
        "source_comparison": comparison,
        "snapshot_date": snapshot.end if snapshot else None,
        "warnings": warnings,
        "metrics": {
            "gross_sales": amount(gross),
            "discounts": amount(discounts),
            "net_discount": amount(net_discount, "signed_net_discount_source_required"),
            "sales_returns": amount(credits),
            "net_sales": amount(
                net, "unassigned_sale_values_missing" if assigned_only else "missing_verified_data"
            ),
            **(
                {
                    "reported_net_sales": amount(reported_net),
                    "reported_net_discount": amount(reported_net_discount),
                }
                if assigned_only or comparison["status"] == "mismatch"
                else {}
            ),
            "cogs": amount(cogs),
            "gross_profit": amount(gross_profit),
            "gross_margin": amount(
                gross_profit / net * 100 if gross_profit is not None and net and net > 0 else None
            ),
            "expenses": amount(expense),
            "operating_profit": amount(operating),
            "sold": amount(
                sum((v[0] for v in motion_sales.values()), ZERO)
                if use_movement
                else sum_field(sales, "sold", demand_complete)
            ),
            "returned": amount(
                sum((v[1] for v in motion_sales.values()), ZERO)
                if use_movement
                else sum_field(sales, "returned", demand_complete)
            ),
            "stock": amount(
                sum((decimal_value(p["stock"]) for p in result_products if p["stock"] is not None), ZERO)
                if snapshot
                else None
            ),
            "inventory_cost_value": amount(
                valuation
                if snapshot and valued == sum(p["stock"] is not None for p in result_products)
                else None
            ),
            "slow_stock_capital": amount(
                slow_capital if snapshot and slow_cost_complete and demand_complete else None
            ),
        },
        "products": result_products,
        "representatives": rep_result,
        "categories": category_result,
        "recommendations": recommendations,
        "rules": rules.model_dump(),
        "sources": [
            {"batch_id": b.id, "report_type": b.report_type, "start": b.start, "end": b.end}
            for b in period + ([snapshot] if snapshot else [])
        ],
    }
