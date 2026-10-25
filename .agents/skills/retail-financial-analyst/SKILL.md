---
name: retail-financial-analyst
description: Define, implement or review retail monetary metrics and financial recommendations. Use for sales, discounts, returns, COGS, profit, margins, inventory valuation, Decimal arithmetic or source financial reconciliation.
---

# Retail financial analysis

1. Read [financial rules](../../../docs/BUSINESS_RULES.md) and approved source mappings. Identify scope, currency/tax basis, period and source authority; never add two reports of the same sale.
2. Validate discount meaning using actual arithmetic and raw evidence, not header labels. Preserve unresolved columns and block affected derived metrics.
3. Use Decimal from strings, explicit normalized signs and approved rounding boundary/mode. Keep sale-return credits and cost reversals separate; prevent double subtraction.
4. Require sale-time verified cost for COGS/profit and complete comparable expenses for operating profit. Return unavailable with reason for missing inputs; do not substitute zero or current retail/purchase price.
5. Define formula, input fields, assumptions, missing behavior, validation and independent fixtures for each added metric. Distinguish gross/net sales, gross profit and operating profit; do not label unsupported net profit.
6. Explain recommendations with subject, observation, evidence, impact, action and data quality. Require verified prices/costs/minimum margin before a numerical discount suggestion.

## Required verification

Execute formula fixtures, Decimal rounding boundaries, return-only/negative and zero-denominator cases, missing/partial cost/expense cases and source total reconciliation. Verify frontend/export money stays exact. Record input completeness, source references and actual command/test results; never report unavailable metrics as zero.
