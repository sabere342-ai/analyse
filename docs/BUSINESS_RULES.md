# Business rules and architecture decisions

## Small application, explicit boundaries

Single-store modular monolith: React/strict TypeScript/Vite UI → authenticated FastAPI → ingestion/normalization, analytics, reporting → one SQLite database/private originals. CSS with logical properties and Lucide icons avoids a UI/state framework dependency before it is needed; React state and one fetch wrapper are sufficient. No sizes/colors, cashier, ERP, SaaS, paid AI, automated POS sync or distributed infrastructure.

Python modules: `extraction`/`pos_pdf` (bounded spatial/native Unicode adapters), `pos_contract` (source-specific reconciliation), `ingestion` (normalization/reconciliation/lifecycle), `analytics` (pure calculations), `reporting` (exports), `auth`, `db`, `backup`, `app`. Source authority and provenance live in DATA_CONTRACTS, not duplicated domain formulas in UI. JSON money is a decimal string; UI never recomputes finance in JavaScript.

SQLite is for one app host/short writes on local disk. Review PostgreSQL for multiple app instances, sustained lock contention or hosted operational needs. Migrate on a restored copy with portable SQLAlchemy/Alembic mappings; compare identities, rows, states, FKs and reconciliation totals before cutover; keep rollback backup. Never copy an active SQLite DB casually or use network-filesystem replicated writers.

## Common metric contract

Inputs must be accepted, explicitly scoped and non-overlapping. Aggregated reports partly intersecting a selected period are excluded, not prorated into invented daily facts. Full period coverage is required for aggregate sales/financial totals and zero-sales claims. Unknown is `unavailable` with reason, never an assumed 0. API includes period, snapshot date, coverage warnings, rule version/values and source references. Supported currencies are EGP/USD/EUR/SAR/AED/GBP, with two minor decimal places; other minor-unit policies are rejected rather than silently rounded. EGP is the visible default; confirm store currency/tax/accounting cutoff before real use. Imports must use the same accounting basis for comparison.

Sales windows and snapshot as-of are independently selected; an out-of-window stock date is disclosed and disables aligned coverage/replenishment. Complete report periods are also compared by source; an unexplained discrepancy preserves separately labeled source money and blocks store units/demand. Owner-confirmed representative-only coverage permits complete movement as store-unit authority after nonnegative per-barcode subset checks. Transfers/purchases/adjustments remain excluded from sold/returned units. Full-store monetary measures remain unavailable; `reported_net_sales` and signed `reported_net_discount` retain the representative report scope. Complete movement can establish zero sales within its window, but cannot establish product age or in-stock history.

All calculations use Decimal from validated strings and exact string storage. Ratios/intermediates retain precision; display rounds HALF_UP to two places. Source reconciliation stays exact and independent; display rounding cannot hide a mismatch. Categories sum unrounded source values before display. Adjustments or unknown sign/discount semantics require source review.

## Finance and representatives

| Metric | Formula / required evidence | Missing/validation rule / tested example |
| --- | --- | --- |
| Gross sales G | Sum verified gross sale values before discounts, consistent tax basis | Do not assume displayed price is unit price; 2×100=200 only if verified |
| Returns R | Sum actual return credits, accounting for returned discount effect | Quantities alone insufficient; credit 45 reduces sales once |
| Discounts D | Sum verified sale discounts, not an assumed meaning of a source label | G=200,D=20,R=45 → net 135; invalid relationship blocks import |
| Signed net discount from POS | Sum source discount including return reversals; source quantity × unit price − signed discount = value | Keep separate from positive-only sale discounts/refund credits; no invented allocation for mixed sale/return aggregates |
| Net sales N | G−D−R, or independently verified source net | Never subtract credits/discounts twice; net-only source does not establish missing components |
| Discount rate | D/G×100 | G≤0 unavailable; 20/200=10% |
| COGS C | Verified sale-time issued cost less return-cost reversals | Latest purchase/retail/inventory unit cost is not historical COGS; 100−25=75 |
| Gross profit/margin | N−C; (N−C)/N×100 | Missing C unavailable; N≤0 margin unavailable; 135−75=60, 44.44% |
| Expenses E | Verified expenses for complete matching period | Missing expense report is unknown, not zero; source can explicitly report a zero expense amount |
| Operating profit | N−C−E | Complete inputs only; 135−75−10=50; no unsupported net-profit claim |
| Inventory cost value | Selected on-hand × most recent verified as-of unit cost | Full cost coverage required; cost source dated after snapshot excluded; no retail valuation substitution |
| Slow-stock capital | Verified slow/dead-classified stock × cost | Insufficient age/availability/cost coverage → unavailable |
| Category contribution | Category net/store net×100; category net itself | Positive denominator, matched currency and scope; unknown category is separate |
| Trend | (current net−prior net)/prior net×100 | Prior equal-length complete comparable period, same currency, prior>0; otherwise unavailable |
| Rep metrics | Attributed G,N,D, sold, returned, N−attributed COGS | Unknown rep separate; sums reconcile to store source |
| Rep return rate | Returned/sold×100, same-period activity basis | Sold=0 unavailable; can exceed100% due to old-period returns; not cohort defect rate |
| Rep ranking | Descending verified net sales, ties share competition rank | No employee efficiency conclusion without comparable shifts/traffic/opportunity |
| Target achievement | Same-period net/explicit positive target×100 | Target must match selected period; no supplied target → unavailable |
| Product contribution per rep | Product attributed net/rep net×100 | Positive verified rep denominator; source evidence retained |

Return attribution is whatever the approved source actually represents (original seller vs processing rep); confirm with owner before real employee evaluation. Employee names are private data. Financial recommendations review negative operating profit, low verified margin, high discounts and elevated returns; no automatic discount percentage or ordering.

## Inventory

| Metric | Formula / evidence | Missing/validation rule / example |
| --- | --- | --- |
| Gross/returned/net units | S, U, Q=S−U | Transfers/subtotals excluded; S=10,U=2 → Q=8; returns-only can make Q negative |
| Current/available stock | Selected snapshot H; A=H−reserved only when reservation semantics confirmed | Missing snapshot/reservation meaning → unavailable; H=10,reserved=3 → A=7 |
| Daily net sales v | Q/complete calendar days | Incomplete feed not zero; 46/23=2 |
| In-stock velocity | Gross sold/verified in-stock days | Only an unambiguous product availability value; do not sum repeated rep availability; 20/10=2 |
| Coverage | A/v | v>0, nonnegative meaningful stock and aligned snapshot; stale snapshot blocks coverage/replenishment |
| Sell-through | Q/(opening stock+external purchases)×100 | Previous-day opening and aligned closing snapshots, complete movement basis, stock recurrence and sale-quantity cross-reconciliation at store scope; unmodeled adjustments/purchase returns block; do not count internal transfers as supply at store scope |
| Top sellers | Descending Q, stable barcode tie order | Incomplete data cannot establish full ranking |
| Zero-sales candidate | H>0, S=0 over complete sales window | Missing feed is not zero; does not establish dead stock |
| Slow/potential dead | Configured velocity/no-sale threshold plus sufficient age/window and verified full availability | New product or stockout periods cannot support the label |
| Replenishment review | ceil(max(0,v×(lead time+target cover days)+safety−A)) | Positive verified velocity, aligned available stock; proposal not purchase order; v2,lead3,target4,safety1,A5 →10 |
| High stock / low demand | Supported coverage above configured max or supported zero/slow candidate | No fake infinity when v≤0; seasonality limitations disclosed |
| Category movement | Incoming/outgoing by category/type/scope | Missing movement coverage unavailable; running balances not flows; transfers do not create revenue |

Store thresholds are visible and configurable; shipped values are editable starting proposals, not owner-approved seasonal policy. Rules retain full values in recommendation evidence. No annual extrapolation from a brief promotion. Each recommendation includes subject, observation, evidence, impact, action and quality status, plus period/rules. Data-quality labels are not invented probabilities.

## Technology/licensing evidence

Exact dependencies are in pyproject.toml/uv.lock and frontend/package.json/package-lock.json. Official PyPI/NPM release metadata verified versions, Python/Node compatibility and supplied license fields during implementation. Python3.12/Node24 environment is exercised; Node24 LTS guidance was read from nodejs.org. Initial official guide-host requests returning403 are historical limitations; registry/maintainer sources supplied alternatives.

pdfplumber is MIT (maintainer LICENSE read), chosen for positional/table extraction without PyMuPDF's AGPL/commercial licensing decision. Actual layouts were compared against independent text inspection: pdfplumber geometry plus PDFium logical Unicode is selected for these layouts. This does not validate unobserved formats. pypdfium2 is explicitly pinned at its previously locked version; wrapper BSD-3-Clause/Apache-2.0 and bundled dependency notices were read (18 files) and remain installed. No python-bidi dependency was added. openpyxl MIT; xlrd BSD; FastAPI/SQLAlchemy/Alembic MIT; Uvicorn BSD; python-multipart Apache; cryptography Apache/BSD. WeasyPrint BSD-3-Clause (maintainer LICENSE read), local native rendering tested. DejaVu Sans Bitstream Vera/public-domain modifications license was read from installed Debian copyright; required notice ships in `madrid/font-license.txt` and is attached to exported PDFs. Keep transitive notices on redistribution; no separate project-wide license is invented.

React/Vite/plugin MIT, TypeScript Apache, Lucide ISC, test package license metadata reviewed. No external skill/plugin installed, no global Codex configuration changed. Historical openai/skills deprecation notice directs examples to openai/plugins; existing four local skills remain small procedures, loaded manually when discovery unavailable. No runtime AI key.

## Operation choices

Private store host: control machine/LAN access, power, updates and encrypted off-device backups. Hosted single app: HTTPS, owner auth, secure cookies, allowed hosts/origin, private local volume, monitoring/backup owner. No deployment performed. Suggested RPO24h/RTO4h are planning targets needing owner confirmation and measured operations, not guarantees. PWA is installable on supported secure origins; caches only static shell and never authenticated business data. See README for tested commands and maintenance-mode recovery.

PDF presentation uses one inventory row per product rather than repeating each product for every metric; source filters, signed discounts, quality warnings, independent stock date and representative values remain visible. CSV/XLSX retain detailed metric/evidence rows. The actual full report was revalidated under the unchanged CPU/memory/wall-time limits after the old repeated layout exceeded its CPU budget.

## Optional cloud runtime

PostgreSQL cloud mode preserves the same Decimal/service formulas and JSON string measures as local SQLite; it changes persistence, not interpretation. Originals and batch/audit state share one transaction. Login throttling is store-wide (one owner), persisted and serialized across instances: ten failed attempts in five minutes, reset after expiry/success. Cloud owner creation requires a hash-verified invitation and cannot replace an existing owner; local-only setup remains unchanged. Sessions are hashed and durable. Encrypted cloud backup uses a repeatable-read snapshot and is verified by restoring rows/originals into a new local store. Cloud restore into a live provider is not performed.

Added psycopg and psycopg-binary3.3.6: official PyPI metadata reports LGPL-3.0-only and no published advisories at verification time; installed license notices remain in the image. Deployment is a private personal Hobby experiment only, per owner clarification. Vercel's Hobby terms restrict commercial use; no Pro/paid activation is authorized or performed.
