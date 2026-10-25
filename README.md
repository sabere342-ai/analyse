# Madrid Retail Intelligence — مدريد

Arabic RTL, mobile-friendly analytics for one clothing store over its existing POS. Modular React/FastAPI application with local SQLite and optional PostgreSQL cloud persistence: reviewable imports, inventory/representative/financial insights, explainable recommendations and PDF/CSV/XLSX exports. No cashier, sizes/colors, ERP, paid AI or automatic POS integration.

**Validation status:** the three supplied Arabic POS reports were inspected locally and their individual rows/subtotals/grand totals validated against private source evidence. The owner confirmed that the representative report excludes unassigned sales. Per-barcode subset checks support that scope: complete movement supplies store sold/returned units, while representative monetary values are labeled separately. Unassigned revenue and unverified COGS/profit remain unavailable. A later stock date blocks aligned coverage/replenishment. Private reports, source evidence, store databases, backups and owner credentials are not included in this repository; a new installation starts empty with no default password.

## Run locally

R2-G local real-POS acceptance now passes: all3 original reports were exercised in an isolated local store with independent source observations, reconciliation, explicit acceptance, analysis, exports, restart and rollback. The full Chromium suite passed5/5 together. See [R2-G scope and evidence](docs/R2G_ACCEPTANCE.md); this is a documented alternative to the unavailable historical all-field golden. Vercel team access is restored and Hobby/protection are confirmed; the update awaits authenticated application and preservation checks because the connected browser cannot start. The earlier R2/R2-F results below are historical.

R2-F current candidate: worksheet scope explicitly distinguishes all from selected; selecting none blocks import. Reinspection preserves deliberate choices, stale source results are ignored, and invalid mapping JSON cannot reuse an earlier mapping. Isolated PostgreSQL18.4/TLS, migrations, Chromium import/export and actual restart persistence are now verified on Windows. Private-source and hosted acceptance remain unavailable. See [R2-F evidence and remaining gates](docs/R2F_CLOSURE.md); the earlier R2 results below are historical.

R2 candidate (2026-10-25, Windows): read-only file inspection, visual column mapping, independent generic subtotals, printed net-total reuse, XLS dates, expired-session handling and Windows parser/backup fixes are implemented. Current evidence and limitations are in [R2 delivery](docs/R2_DELIVERY.md). Historical private-file/cloud checks below describe earlier environments; this checkout does not contain those private inputs.

On Windows, use Python 3.12 and Node 24, `uv sync --frozen --python 3.12`, then `npm --prefix frontend ci --ignore-scripts` and `npm --prefix frontend run build`. Start with `.venv/Scripts/python.exe -m uvicorn madrid.app:create_app --factory --host 127.0.0.1 --port 8000`. For PDF exports install the native Pango libraries described in the [official WeasyPrint Windows instructions](https://doc.courtbouillon.org/weasyprint/latest/first_steps.html#windows) and set `WEASYPRINT_DLL_DIRECTORIES` to their directory. This run used the checksum-verified official WeasyPrint70.0 Windows onedir DLLs in ignored `.cache/weasyprint-runtime/onedir/weasyprint/_internal`; no global runtime/security configuration was changed. Browser tests accept `MADRID_BROWSER` or Playwright's installed Chromium and create an isolated local store on either platform.

Tested environment: Debian13 x86_64, Python3.12.14, Node24.19.0, npm11.9.0. Use a supported Node24/Python3.12 environment and uv; exact dependencies are locked. WeasyPrint requires system Pango/fontconfig/DejaVu Sans (available here); Chromium is needed only for browser tests. On another Linux machine install reviewed OS packages from its trusted repository before running. No package-signature/TLS bypass.

From the repository root:

```sh
UV_CACHE_DIR="$PWD/.cache/uv" uv sync --frozen
npm --prefix frontend ci --ignore-scripts --cache "$PWD/.cache/npm"
npm --prefix frontend run build
XDG_CACHE_HOME="$PWD/.cache" .venv/bin/uvicorn madrid.app:create_app --factory --host 127.0.0.1 --port 8000
```

Open the local service on port8000 in your browser. First visit creates the single owner password (12+ characters) through local-only setup; no seeded/default password. Sign in, import a file, inspect raw/normalized rows and totals, then accept. Migrations run at startup. Data/originals live privately in ignored `data/`. No test/demo data is loaded into the real database automatically.

Development: run backend as above and `npm --prefix frontend run dev` separately; Vite on loopback proxies `/api` to8000. Rebuild before serving the production shell through FastAPI.

## Import, review and correct

Selecting or dropping a file now inspects its signature and structure before staging. The inspection shows filename/size, pages or worksheets, source headings and preview rows, with `RECOGNIZED`, `NEEDS_MAPPING`, `NEEDS_REVIEW`, `UNSUPPORTED` or `INVALID`. Recognition means structural compatibility, not acceptance or verified business semantics. Select data worksheets and use the column dropdowns for unknown headings; advanced JSON mapping remains supported. After changing CSV encoding/delimiter, press the reinspection button. Inspection uses temporary local scratch only and creates no batch, durable original or dashboard facts. Extraction still stages an immutable candidate; review, reconciliation and explicit acceptance remain separate.

Choose snapshot/sales/movement/costs/expenses/targets, source period, currency and scope. Snapshot/cost dates must match. Download the clearly synthetic template for column examples, or map canonical fields to source headings. CSV UTF-8/Windows Arabic and delimiter selection are supported; XLS/XLSX and multi-page table PDF have bounded local adapters. Arabic POS snapshot/sales/movement layouts are detected by title and fixed column signatures, with native Unicode cell decoding and printed-period validation; custom mapping is for the generic adapter.

Enter independent source totals and confirm coverage. The inspected POS profile reads its independent printed totals automatically and validates each source subtotal/chain as well; explicit totals cannot override a source mismatch. Financial/reservation/availability semantics require explicit confirmation. Missing/ambiguous codes, Excel numeric codes, formulas, unknown layouts and reconciliation mismatches block acceptance. Review raw cells, page/sheet/row locators, exclusions, checksum and normalized records. Correct/re-map and reimport with explanatory note when needed; do not alter an original to pretend a mismatch disappeared.

Exact reupload returns the existing batch; changed parser/config stages a new interpretation. Overlapping accepted coverage is blocked. To replace, rollback the prior batch with a reason, then accept the validated new candidate. Rejected/rolled-back history remains. For a representative-only sales report choose `sales_coverage=assigned_only` and record the owner confirmation in the source note; a complete movement report is required for store demand. Scope is an exact population filter; do not mix partial rep/warehouse reports under complete store scope. Costs/expenses/targets use the same review workflow; inventory cost never substitutes historical COGS.

Before acceptance, the review compares new/existing barcode identities against accepted data in the same scope, shows stock differences from the preceding snapshot and blocks overlapping coverage. Pending files are counted separately and do not contribute to the dashboard. After acceptance or rollback, the app reloads persisted facts with report-appropriate dates; use the review's analysis button to see the updated results and recommendations. A newer snapshot supplies the latest balance rather than adding balances together.

The analysis period and stock as-of date are independent filters. Login and acceptance select accepted report dates automatically, including stores with only a stock snapshot. The UI can read the printed period from recognized PDFs (`source_dates=report`); generic formats keep entered dates. Editing filters prepares the next query; press Update Results to apply them. Exports use the period of the displayed result. A next-day snapshot is displayed with its own date and is never silently treated as an earlier closing balance. Source comparisons keep representative-report sales and inventory sale/return movements separate. The POS Discount column is a signed net discount including return reversals; it is displayed separately from an unavailable gross sales-discount/credit breakdown.

## Verify

```sh
.venv/bin/ruff check madrid migrations tests
.venv/bin/ruff format --check madrid migrations tests
.venv/bin/mypy madrid
.venv/bin/pytest -q --tb=short
npm --prefix frontend run format:check
npm --prefix frontend test
npm --prefix frontend run build
npm --prefix frontend run e2e
npm --prefix frontend audit
git diff --check
```

PostgreSQL integration tests use `MADRID_TEST_DATABASE_URL` for a dedicated test database with schema-creation privileges; they create/remove only isolated synthetic schemas. Set `MADRID_DATABASE_CA_FILE` only when that test server uses its own trusted CA. Without the test database, those cases explicitly skip. Never treat skips as cloud-persistence validation.

E2E uses installed `/usr/bin/chromium`, or `MADRID_BROWSER` pointing to a compatible installed binary. The test starts/stops its own server, uses a fresh `/tmp/madrid-e2e-*` directory and checks desktop/mobile/auth/import/rollback/exports/PWA. It never uses the real store DB. Private actual-report acceptance reads the ignored `samples/private/acceptance.json` (override with `MADRID_PRIVATE_SPEC`) and compares every row with checksum-linked pre-adapter source observations. These tests execute here; environments without private files report explicit skips instead of claiming source validation.

## Encrypted backup and restore

Stop imports/server during maintenance to coordinate source retention with the database snapshot. From repository root:

```sh
.venv/bin/python -m madrid.backup create backups/store.mri --directory data
.venv/bin/python -m madrid.backup restore backups/store.mri --directory data-restored
```

Passphrase is entered through a hidden terminal prompt, never a command argument. Keep it securely outside the archive. Backup uses a consistent SQLite snapshot, verifies referenced original hashes, creates a manifest and encrypts with scrypt/AES-GCM. Restore requires a new directory, checks authenticated encryption/hashes/DB integrity and invalidates sessions. Test restored totals before switching `MADRID_DATA_DIR` to it. Existing destinations/backups are never overwritten. Retention, off-device storage and recovery objectives need owner operational policy; do not put backups in Git.

## Configuration and operating limits

No AI/API key required. Optional non-secret runtime variables: `MADRID_DATA_DIR`, `MADRID_ALLOWED_HOSTS`, `MADRID_ORIGIN`, `MADRID_SECURE_COOKIE=1` behind approved HTTPS. Default binding is loopback; public deployment is not performed. Configure trusted host/origin and secure cookies plus private storage, updates and backups before any network exposure. SQLite supports one app host; PostgreSQL review is needed for concurrent multi-instance operation.

PWA caches static shell only; authenticated reports/data are not offline. Browser installation is supported where secure-origin/browser rules permit, verified here in Chromium normal profile.

## Private personal experiment on Vercel

The owner explicitly chose private personal testing on Hobby and prohibited Pro or any paid subscription. The complete app is now deployed as a protected **Preview** at [https://madrid-retail-preview-h99624697-8296.vercel.app](https://madrid-retail-preview-h99624697-8296.vercel.app), backed by a Neon `free_v3` database connected to Preview only. Unauthenticated access redirects to Vercel sign-in; app data has its own owner authentication. No private store data was migrated or uploaded. No owner/password was seeded during deployment; the owner has since activated their account. Use the same owner password on the updated Preview. The original activation file remains private in ignored `.vercel/activate-owner.html`; never include that file or its URL fragment in Git/build inputs. Hobby remains for the stated non-commercial personal experiment.
Cloud mode uses `MADRID_DATABASE_URL` (PostgreSQL, TLS `verify-full` with the system CA bundle). Set `MADRID_DATA_DIR=/tmp/madrid-runtime` and `XDG_CACHE_HOME=/tmp/madrid-cache`; this disk is parser/font scratch only. Raw originals commit in the same database transaction as staged rows. Sessions, rules, owner, audit and store-wide login throttling are durable too. Transaction advisory locks serialize acceptance across instances and migration startup. Local mode keeps SQLite and immutable originals on its private disk. No financial formulas or source discount semantics change between modes.

`Dockerfile` builds the entire app with locked dependencies, native PDF/font libraries, an unprivileged UID10001, health check and one worker. The local image build and native browser import/export flow passed. This sandbox's Docker network needed explicit DNS for its existing proxy and the existing system CA bundle mounted as a temporary build secret; no TLS/checksum/signature verification was disabled and no custom CA was embedded in the runtime image. Source files are copied with the runtime user's ownership. `.dockerignore` excludes private store data and caches.

Generate a fresh full-app source package:

```sh
node frontend/prepare-vercel.mjs
```

The printed temporary directory contains only allowlisted source/build inputs, a generated `Dockerfile.vercel`, and a single container service routing all requests to the app. It sets `MADRID_REQUIRE_CLOUD_DATABASE=1`, so missing cloud credentials stop startup rather than silently creating a temporary SQLite store. Authenticated source dry-run and the actual remote container build completed successfully. The old optional argument `node frontend/prepare-vercel.mjs https://YOUR-REAL-BACKEND-HOST` still stages compiled assets for a separately hosted persistent backend; a placeholder origin is never deployed.

Marketplace terms were accepted by the owner; only the verified free database plan was provisioned and connected to Preview. Keep the database URL secret and Preview SSO protection enabled. Configure trusted hosts (`MADRID_ALLOWED_HOSTS`) and, for a custom domain, its exact HTTPS origin (`MADRID_ORIGIN`). Preview origins are derived only from validated platform `VERCEL_URL`/`VERCEL_BRANCH_URL` hostnames, secure session cookies (`MADRID_SECURE_COOKIE=1`), and a 4MiB upload limit (`MADRID_MAX_UPLOAD_BYTES=4194304`) below the function request-body ceiling. The UI reads the actual limit from auth status. Local uploads retain the default20MiB maximum. Do not turn on paid resources or promote this private experiment into a commercial deployment.

Cloud first-owner setup requires a generated invitation: store only its SHA-256 as `MADRID_SETUP_TOKEN_HASH`, give the owner the corresponding `#setup=...` activation link privately, and let them choose their own password. The invitation is sent only to the setup endpoint and removed from the address after success. An existing owner cannot be overwritten by reusing it. No default owner/password is seeded. PostgreSQL originals and normalized facts are private authenticated application data, never static assets.

The live protected Preview passes health200, initialized cloud-owner status200 with a4MiB cap, unauthorized data/comparison401, valid-origin mutation boundary, new workflow asset checks, no-store API checks and SSO302 without credentials. The owner uses their existing password. Actual private reports were exercised through the UI on an isolated local store, including auto dates, acceptance, joined analysis and supported advice; no private reports or test records were uploaded into the live store for validation. Direct headless HTTPS navigation from this sandbox still has its pre-existing browser trust-store limitation; verified-TLS HTTP checks pass.

The stable protected URL is `https://madrid-retail-preview-h99624697-8296.vercel.app`. Future code updates must explicitly deploy `--environment preview` and repoint only this project's alias using `vercel alias set NEW_PREVIEW_URL madrid-retail-preview-h99624697-8296.vercel.app --scope h99624697-8296`. Keep its exact `MADRID_ORIGIN` and existing SSO protection; deploy only the allowlisted temporary source package, never the repository/store directory. Existing owner/data and the free plan must be preserved.

Encrypted cloud snapshots are supported through the existing backup format:

```sh
.venv/bin/python -m madrid.backup create backups/cloud.mri --directory data --cloud
```

This reads the configured cloud URL securely from the environment, takes a PostgreSQL repeatable-read snapshot and creates an encrypted archive of rows/originals. Restore still targets a **new local directory only** with the existing command; it never overwrites a live cloud store. Recovery into another cloud database requires a separately reviewed migration.

## Project references

- [AGENTS.md](AGENTS.md): engineering instructions and current authorization.
- [PLAN.md](PLAN.md): delivery status and remaining external input.
- [DATA_CONTRACTS.md](docs/DATA_CONTRACTS.md): schemas, provenance, normalization, reconciliation, idempotency and security.
- [BUSINESS_RULES.md](docs/BUSINESS_RULES.md): formulas, missing-data rules, architecture, licenses and operations.
- [VERIFICATION.md](docs/VERIFICATION.md): actual evidence, scenario coverage, historical audit and private acceptance.

Private expected originals stay under ignored `samples/private/`: `مبيعات المندوبين بالاصناف.pdf`, `حركة تفصيلية للمخازن.pdf`, `جرد المخازن.pdf`. Their current layouts have been inspected; treat every new upload as untrusted data and revalidate signatures, periods and totals. Do not generalize this validation to changed layouts or generalize the owner-confirmed scope explanation to a new unexplained mismatch.
