# R2 local functional delivery — 2026-10-25

Verdict: `PARTIAL_MADRID_R2_FUNCTIONAL_DELIVERY`.

The supplied directory was a source archive without Git metadata, dependencies, private reports or a local store. Recovered Git metadata from `sabere342-ai/analyse`; the initial files matched `main` at `a4c618c1f0fbfb902eb1692d687d5d9a87cdfd55`. Work stays on `codex/madrid-r2-import-reliability`. No existing file was replaced during recovery.

| Problem | Cause | Delivered behavior | Verification |
| --- | --- | --- | --- |
| Windows startup/parser failure | Unconditional Unix `resource` import; locale-dependent worker output | Windows Job Object CPU/memory/process limits, retained Unix limits, explicit UTF-8 worker transport | Actual Windows API imports, exports and Chromium journeys |
| Unknown columns required manual JSON | No pre-staging structural inspection | Authenticated temporary inspection, explicit statuses, sheet previews/selection, visual mapping, drag/drop and reinspection | Unknown CSV browser journey; mixed-sheet API regression; invalid signature/auth checks |
| Correct grand total could hide bad groups | Generic subtotals were excluded without validation | Independently compare consecutive groups by sheet, exact differences and locators; preserve specialized nested POS validation | Bad offsetting subtotals blocked; signed return/discount and nested POS regressions |
| Formula footer escaped the row gate | Formula check came after header/footer classification | Formula warning applies to every row, including footers | Formula-footer regression blocks acceptance |
| Printed money total had to be retyped | Only primary quantity footer was reused | Net footer can supply independent expected money only when every selected sheet supplies it; explicit inputs cannot waive source checks | Exact net-footer regression plus existing per-sheet mismatch cases |
| Legacy XLS dates failed normalization | Date cells arrived as Excel serial numbers | Convert only typed date cells using workbook epoch; numeric/date/boolean barcodes still need a text source | Actual XLS API fixture with a date cell |
| Backup failed on Windows | SQLite context managers commit but do not close connections | Close source/snapshot/restore connections explicitly before deleting only the generated temporary snapshot | Encrypted recovery, no-overwrite and corrupt-original cases |
| Expired sessions left private UI visible |401 errors did not update app authentication state | Expiry clears private state and invalidates pending requests; failed logout explains that server revocation is unconfirmed | UI event regression and browser authentication journey |

Import engine: parser1.3.0, contract1.2.0; originals/checksums, exact strings, occurrences, immutable revisions, explicit acceptance and overlap locks remain intact. Inspection creates no stored batch or original. Headers are sought in the first50 extracted rows of each sheet; unseen layouts remain mapping/review candidates. Generic subtotals mean consecutive groups, whereas POS item/representative/category/report totals retain their dedicated nested checks. Unknown nested/cumulative layouts are not automatically accepted.

Excel/PDF/CSV: retained bounded PDF/native-text profiles and XLSX formula/ZIP safeguards; added XLS date handling, strict CSV quoting, UTF-8 subprocess transport and actionable encoding/signature/resource messages. Numeric Excel codes are never zero-padded. Scanned PDFs have no trusted OCR path; obtain a native-text PDF or source spreadsheet. No external report/OCR/AI upload was introduced.

UI: a separate import-inspection component supplies previews, sheet checkboxes and field dropdowns; advanced JSON stays editable. Reconciliation shows source value, calculated value, exact difference and source locator. Invalid numeric rows include column, original input and expected format. Existing accepted/pending separation, independent stock dates and displayed-filter export semantics remain.

Analytics: no formula/policy changes. Decimal calculations, missing costs/expenses, transfers, signed returns, source-specific monetary coverage and barcode identity remain under existing regression checks. Unknown profit remains unavailable. No performance improvement is claimed without a comparative measurement. New extraction bounds include4 million characters and100,000 physical rows; existing10,000 nonempty rows/100 columns, wall-time and memory gates remain.

Security/recovery: authentication, HttpOnly cookies, CSRF/Origin checks, durable server sessions, encrypted backup and static-shell-only PWA remain. Windows resource limits fail closed if unavailable. Native PDF DLLs were obtained from the official WeasyPrint70.0 release and checked against its SHA-256 (`ab1151f210b4e6bb7aa7a79e91a67e8ddb760094c107bfda55241b6aaefe7d53`), inside ignored local cache. No global trust/security changes or new application dependencies.

## Executed checks

Windows environment: CPython3.12.15, Node24.19.0, official WeasyPrint70.0 native DLLs and Chromium156. Commands below used the project virtual environment and local Node24 on PATH.

| Command | Exit | Actual result |
| --- | --- | --- |
| `uv sync --frozen --python 3.12` |0| Locked environment installed |
| `npm --prefix frontend ci --ignore-scripts` |0|108 packages audited; zero reported vulnerabilities |
| `.venv/Scripts/python.exe -m pytest -q --tb=short -ra` |0|93 passed,15 skipped; eight absent PostgreSQL cases and seven absent private-report cases |
| `.venv/Scripts/ruff.exe check madrid migrations tests` |0| Passed |
| `.venv/Scripts/ruff.exe format --check madrid migrations tests` |0| Passed |
| `.venv/Scripts/mypy.exe madrid` |0|14 source files checked |
| `npm --prefix frontend run build` |0| Strict TypeScript and Vite production build |
| `npm --prefix frontend test` |0|10 UI tests passed |
| `npm --prefix frontend run format:check` |0| Passed after correcting formatting |
| `npm --prefix frontend run e2e` |0| Four Chromium journeys passed,41.3s |
| `git diff --check` |0| No whitespace errors |
| `.venv/Scripts/python.exe .cache/r2_restart_smoke.py` |0| Actual HTTP server restart retained stock7.00; rollback/rejection passed; CSV3098B/XLSX6430B/PDF810956B; absent profit unavailable |

The restart smoke used its own temporary synthetic store and stopped only its two owned server instances. A separate empty review instance is running at `http://127.0.0.1:8000` with `MADRID_DATA_DIR=.cache/r2-local-runtime`; health/root200 and owner-uninitialized status were verified. It is not connected to the owner's Neon store.

The first full backend run found three failures: a new generic-subtotal check conflicted with nested POS groups, and two backup cases exposed Windows open-file handling. Those paths were repaired, the five affected tests passed, then the full final backend run passed with the explicit skips above. No failed attempt is counted as a pass.

## Functional acceptance

| Input/workflow | Actions and expected outcome | Actual outcome |
| --- | --- | --- |
| Synthetic unknown CSV with quoted comma and leading-zero code | Inspect without staging, map three fields, reconcile, accept, show stock7, reload, export | PASS in Chromium; no inspection batch; exact stock and barcode retained |
| Synthetic XLSX with independent sheet headers | Inspect sheets, retain header isolation, select data sheets and reconcile separately | PASS in API regression suite |
| Synthetic XLS expenses | Read typed dates, reconcile exact amount, preserve financial confirmation | PASS in API regression |
| Synthetic multi-page PDF | Extract rows and independently validate totals | PASS in existing API suite |
| Synthetic stock/sales | Accept, join by barcode, retain unavailable money, apply dates, show recommendations | PASS in Chromium |
| Synthetic reports/exports/recovery | CSV/XLSX/PDF, audited rollback/rejection, encrypted restore to a new destination; no overwrite | PASS in backend/browser checks |
| Mobile/keyboard/PWA | Responsive layout, authenticated workflow and static-only cache | PASS in Chromium; mobile screenshot inspected |
| Three private Arabic POS PDFs | Native import/reconciliation/acceptance | NOT_RUN: sources and checksum-linked private expectations absent here |
| PostgreSQL durability/TLS/concurrency | Isolated dedicated database | NOT_RUN: `MADRID_TEST_DATABASE_URL` absent |
| Protected hosted Preview | Read project and verify candidate safely | BLOCKED: connector403 for existing team; no deployment/alias/database change |

Preservation: no pre-existing local store or private source was present in this checkout. All test credentials, uploads, database rows, backup/restore and temporary-file removal targeted isolated synthetic stores. The real owner/account, accepted imports, audit, Neon database and protected Preview were never written to or reset. Their live contents were not independently audited. No private files, databases, activation materials, credentials or runtime binaries enter the commit. No paid plan/resource, production deployment, merge, history rewrite or user-data deletion occurred.

Remaining gaps: actual private-layout acceptance on this candidate; dedicated verified-TLS PostgreSQL integration; protected Preview access and hosted acceptance; unsupported scanned/nested unknown layouts. General authentication redesign, OCR, broad screen restructuring and new analytics formulas were unnecessary for this bounded working improvement and are not claimed delivered. This is not full R2 acceptance.
