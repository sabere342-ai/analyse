# R2-G real POS acceptance — 2026-10-25

Verdict: `PASS_MADRID_R2G_HOSTED_FUNCTIONAL_VERIFIED`. Local real-POS acceptance passed; the updated protected Preview now has owner-assisted read-only functional acceptance, corroborated by deployment/source metadata and runtime HTTP logs. This is not a full-field historical golden or a live private-report import/export test.

Runtime/source/test candidate: `2fc5d3e99f145ce3a21533a0a6706ad2543f6981` on existing branch `codex/madrid-r2-import-reliability`, Draft PR#1, repository `sabere342-ai/analyse`. Local, direct remote and PR heads matched; the starting tree was clean. No application, dependency, schema or test implementation was changed. The follow-up commit only records newly completed acceptance; runtime equality with the tested candidate is independently checked.

## Actual originals and independent source evidence

The three originals are now present in ignored `samples/private/`. They were read locally and never uploaded to an external service. All40 pages were rendered and visually reviewed for layout, repeated headings, continuation/group boundaries, signs and totals. Original SHA-256 values were checked before/after the entire workflow and remained unchanged.

| Source | Pages | SHA-256 | Local functional result |
| --- | --- | --- | --- |
| جرد المخازن.pdf |9|`2bda8ece62360052e248fed798114a6f007946873067843408444c5c7028430c`|PASS |
| مبيعات المندوبين بالاصناف.pdf |10|`7483ae60a3769d196083097db6a3d4666d796ed47e7e886982ca9bb29006c4b9`|PASS |
| حركة تفصيلية للمخازن.pdf |21|`3d69fe3fa00c3a17bb0fe027a4c4a52fe3867902570d76ad6cb487796c6e1ceb`|PASS |

Historical `acceptance.json` was not found and `MADRID_PRIVATE_SPEC` was unset. It was not manufactured. The seven legacy golden-fixture tests were not run or claimed passing. The user-authorized alternative uses separately recorded source observations made **before consuming application output**:

- A standalone full-page native-text reader independently collected372 inventory and141 representative-sales numeric occurrences, barcode strings and representative grouping, then reconciled the two stock footers,138 item subtotals,3 representative totals and2 printed sales grand summaries. It checked sold−returned and signed price/discount/value arithmetic on every sales detail.
- A separate physical glyph/grid reader, using original PDF vector boundaries rather than application table/normalization results, independently collected343 movement occurrences: barcode, date, operation, reference, warehouse, all quantity/value cells. It checked12 category subtotals, the grand total and239 paired quantity/value running-chain relationships. Running balances were never summed as movements.
- Staged application details were compared by physical page and occurrence-aware field tuples to all856 independently observed numeric records. Legitimate repeats were retained. Inventory name/category token content matched all372 source labels; movement name token content matched all343 source labels. Text order and sales names were visually sampled across the pages. Token equality does not assert exhaustive logical-order validation of every name.

This is an explicitly bounded alternative acceptance, **not an exhaustive856-row/all-field historical golden**. Source values, employee identities, private observations, parser comparisons, logs, screenshots, exports, test credentials and test databases remain under ignored private/cache paths. No private observations were copied from application output to become expected values. The source-reader code does not import `madrid`.

## Actual browser and persistence workflow

The real frontend and FastAPI ran on a new private local SQLite store with isolated owner credentials. Each original was uploaded through the UI; profile/type, complete page count, printed period/date, raw/normalized provenance and independent checks were verified before explicit acceptance. The representative source was explicitly marked assigned-only using the owner's confirmed business rule.

| Gate | Result |
| --- | --- |
| Real-file inspection, parsing, independent reconciliation and explicit acceptance, all3 reports |PASS |
| Barcode joins and all372 stock/available balances against the source |PASS |
| Movement sale/return units, with transfers excluded; representative subset/group checks |PASS |
| Full-store revenue/COGS/profit/expenses remain unavailable; representative money stays scoped |PASS |
| Independent stock as-of date; unsupported coverage/replenishment unavailable |PASS |
| Recommendations have evidence/action/quality; no unsupported dead-stock or zero-sale conclusions |PASS |
| CSV/XLSX downloads match every exported row, displayed summary metric/status and product quantity |PASS |
| PDF download,25 pages, includes every stock barcode and displayed summary/representative amounts; first/last pages visually inspected |PASS |
| All3 identical original reuploads return the same accepted batch IDs; still3 interpretations |PASS |
| Stop/restart actual server: all logical tables hash-identical; same session and dashboard after reload |PASS |
| Explicit UI rollback on the isolated movement batch; audit recorded; unaffected stock/scoped sales retained |PASS |
| Original file checksums unchanged; zero external report uploads |PASS |

Private acceptance server instances were stopped after verification. The pre-existing review instance on port8000 was not replaced or seeded; its all-table logical fingerprint still matches the earlier preservation snapshot. The actual store/Neon database and owner account were not used for testing.

## Aggregate Chromium closure and commands

`npm --prefix frontend run e2e` ran once against the unchanged corrected candidate, with existing Node24.19.0, Chromium, Python3.12.15 and the previously installed native PDF libraries. **Aggregate exit0:5 passed,0 failed,40.8s.** This closes the earlier combined-run gap, covering authentication, inspection, worksheet selection, mapping, explicit acceptance, actual duplicate reupload, dashboard refresh, export, rollback, mobile and static-only PWA behavior. No new correction or assertion weakening was necessary.

| Executed command | Exit | Evidence |
| --- | --- | --- |
| `.venv/Scripts/python.exe .cache/r2g_inspect_sources.py` |0| Source hashes/page metadata and local renders |
| `.venv/Scripts/python.exe .cache/r2g_observe_native.py` |0| Independent source observations and totals/chains |
| `.venv/Scripts/python.exe .cache/r2g_real_acceptance.py` |0| Actual UI import→source comparison→acceptance→analysis→exports→restart→duplicate/rollback |
| `.venv/Scripts/python.exe .cache/r2g_check_analysis.py samples/private/r2g-evidence/accepted-analysis.json samples/private/r2g-evidence/exports` |0| All-source analysis and CSV/XLSX parity; PDF summary/representative values and inventory barcode completeness |
| `npm --prefix frontend run e2e` |0|5/5 combined Chromium journeys |
| `.venv/Scripts/python.exe .cache/r2f_review_snapshot.py after` |0| Original review-store logical tables unchanged |
| `git diff --check` |0| Clean whitespace |

Acceptance helpers/evidence are retained locally in ignored paths. The source reader needed corrections for actual bidi text ordering and rectangle edges; those source-reader attempts were not counted as passing and did not modify application behavior, source files or expected application results. No application changes invalidate R2-F's isolated PostgreSQL18.4/TLS1.3/migration001→002 evidence, so PostgreSQL was not restarted/retested. The earlier backend/UI counts remain historical, not fresh R2-G suite claims. No dependencies were reinstalled and no remote CI was triggered.

## Hosting recovery and delivery boundary

Initial read-only provider discovery independently confirmed project `prj_HAiJ4tehk8EdHqw4wXHd0jxKZd7f`, name `madrid-retail-intelligence`, owning account/team `team_Mxb8xgtqsSPG0KLkh7l9qZv5`. Project-list visibility did not support a deletion claim. Connector identity is `h99624697-8296` (`ZMNRyK7svhiH0SFpBIGm7Ulj`); initially, authorized team listing was empty and scoped project-detail access returned403 requiring team authorization. CLI remains a different identity, `sabere342-9142`, with no local project link. No CLI account switch or global authentication change was attempted.

After the owner approved a fresh supported consent, live connector calls successfully retrieved the project, its owning team, deployment, Preview environment metadata and stable alias. Authenticated-user metadata confirms active Hobby billing with no trial. Before deployment, the owner explicitly confirmed successful login and existing data on the old stable Preview, deployment `dpl_3DEZt11v9QMQkQNo3gPpVyynTPgW`. Project SSO remains enabled for `all_except_custom_domains`. All23 listed environment variables target Preview, including the existing sensitive `MADRID_DATABASE_URL`; their IDs/types/targets/update timestamps are unchanged before and after deployment. Credentials were not decrypted or changed. Consent links are temporary and excluded from public evidence.

The existing allowlisted packager staged42 files,570054 bytes, from source head `90f7e8e962d026b0a3f8054de0d176b3744c0131`; all copied source files still matched deployment head `d7e78664f28c793824c75e15842d00d84f3a5904`, whose intervening changes were documentation only. Generated container configuration requires cloud persistence and uses temporary disk only for scratch. Manifest SHA-256: `0c417acaa094ddfc31a7f44c56b199fcf313560924e17232b4ac86d349939b3d`. Only these public source/build inputs were sent to Vercel. The provider's source tree independently matches all42 file paths and SHA-1 digests; no private reports, databases, backups, activation files or credentials were included.

## Protected Preview acceptance — 2026-10-26

Deployment `dpl_DDR2eQVKoeNWxckmBfqdVpPsesNj`, URL `https://madrid-retail-intelligence-vw55qavu5-h99624697-8296.vercel.app`, completed its remote container build and is READY, Preview (`target=null`), tied to source head `d7e78664f28c793824c75e15842d00d84f3a5904`. Container image digest: `sha256:1825f64d53bf50afe90ab04668f37c2904db852848bc4267865c8f4a25a5ee5a`. The API's documented omitted-target Preview semantics were checked against current official documentation before creation; no Production target or paid build-machine override was sent.

The owner initially reported a connection timeout. A later screenshot from this exact deployment's `/api/health` showed `{"status":"ok"}`; runtime logs independently confirm health200. The owner then explicitly confirmed login with their existing password and appearance of their usual data on the new URL. The stable alias was changed only after those checks. Provider alias readback now maps `madrid-retail-preview-h99624697-8296.vercel.app` to `dpl_DDR2eQVKoeNWxckmBfqdVpPsesNj`; the old deployment was retained.

| Hosted gate | Evidence and result |
| --- | --- |
| Exact existing project/team, active Hobby, Preview target, retained SSO | PASS: independent provider metadata before/after |
| Remote container build and intended source version | PASS: READY, matching commit,42 source digests and image digest |
| Health and authenticated reads | PASS: deployment-scoped runtime logs show GET health/auth-status/batches/analytics200 and POST login200 |
| Authentication rejection | PASS: runtime logs also show a rejected login401 before successful login; no password reset occurred |
| Current UI assets | PASS: runtime logs show200 for `index-CQCiXotU.js` and `index-DV2exS5q.css`, matching the locally verified build |
| Existing owner/data across old and new deployment | PASS within observed scope: owner confirms existing password and usual data before/after, unchanged database-link metadata, new deployment serves authenticated stored-data reads. No exhaustive cloud-table fingerprint is claimed |
| Unauthenticated protection, new URL and final stable alias | PASS: verified-TLS GET `/`, `/api/health`, `/api/auth/status`, `/api/batches` returns302 to Vercel login |
| Stable alias conversion | PASS: performed after new-deployment checks; provider readback confirms exact new deployment |
| Agent-controlled authenticated hosted browser journey | NOT_RUN: connected browser kernel cannot start; acceptance used owner interaction plus independently queried runtime logs |
| Actual hosted private-report imports/exports or destructive test records | NOT_RUN: private originals remain local; no live test imports/rollback were performed |

The connected browser initially failed with `windows sandbox failed: helper_unknown_error: setup refresh had errors`; a later retry after the tool update failed with `trusted Node process exited unexpectedly`. Share links, protection bypass tokens and extracted browser credentials were not used. An initial one-hour runtime-log query failed the Hobby retention boundary; the corrected30-minute query returned actual logs. No errors/fatal logs matched the queried30-minute window; this is bounded evidence, not a general absence-of-errors claim.

Review-store logical preservation was checked again and passed. Runtime/tests remain unchanged from the accepted local candidate; already completed application/PostgreSQL/browser suites were not repeated. Existing hosted database linkage and owner credentials were preserved; source/metadata and owner-visible checks do not assert a byte-for-byte cloud database snapshot. No replacement project/database, environment/protection change, paid service, Production deployment, private-report upload, owner reset, accepted-live-data test mutation or PR merge occurred. PR#1 stays Draft; previous commits/main are preserved. Runtime receipts and private operational evidence remain under ignored cache paths.
