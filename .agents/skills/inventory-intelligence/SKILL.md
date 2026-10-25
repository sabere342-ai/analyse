---
name: inventory-intelligence
description: Define or review stock metrics, demand windows and explainable inventory recommendations. Use for sales velocity, coverage, sell-through, slow or dead stock, zero-sales classification, stockouts and replenishment candidates.
---

# Inventory intelligence

1. Read [inventory contracts](../../../docs/BUSINESS_RULES.md). Select one snapshot/as-of scope and verified sales window; label stale evidence and gaps. Never treat balance/subtotals as movement or transfers as sales.
2. Distinguish sold, returned and net units. Confirm calendar-day vs availability-adjusted velocity; do not infer in-stock history from one ending snapshot.
3. Require complete coverage before claiming zero sales and adequate age/availability before classifying potentially dead stock. Keep insufficient history, missing data and actual zero distinct.
4. Use versioned owner-approved thresholds, lead-time/target assumptions and explicit discrete-unit rounding. Verify supply basis before sell-through; label seasonality/promotion limitations.
5. Produce review candidates, not automatic purchases/pricing. Include subject, observation, source/window evidence, impact, action and quality status. Use financial skill before cost/tied-capital or discount calculations.

## Required verification

Execute each affected metric fixture and T16–T19, new-product, stockout, return-only, missing-period, zero-denominator, stale-snapshot and rule-boundary cases. Verify identical data/config produces identical recommendation evidence. Record actual checks and unresolved coverage; do not equate no row with no demand.
