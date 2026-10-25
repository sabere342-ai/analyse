# R2-G real POS acceptance — 2026-10-25

Verdict: `PASS_MADRID_R2G_LOCAL_REAL_POS_ACCEPTED`. Vercel team access is restored; updated hosted acceptance remains blocked on authenticated application and preservation checks. This is local acceptance on isolated data, not a deployment or a full-field historical golden claim.

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

After the owner approved a fresh supported consent, live connector calls successfully retrieved the project, its owning team, deployment, Preview environment metadata and stable alias. Current authenticated-user metadata confirms active Hobby billing with no trial. Existing deployment `dpl_3DEZt11v9QMQkQNo3gPpVyynTPgW` is READY and Preview (`target=null`); stable alias `madrid-retail-preview-h99624697-8296.vercel.app` still points to it. Project SSO remains enabled for `all_except_custom_domains`. All23 listed environment variables target Preview, including the existing sensitive `MADRID_DATABASE_URL`; credentials were not decrypted or changed. Environment metadata proves configuration presence, not database reachability or logical data preservation. Consent links are temporary and excluded from public evidence.

Verified-TLS requests without credentials to `/`, `/api/health` and `/api/auth/status` each return302 to Vercel login. No protected application response or health200 is claimed from those redirects. The connected browser tool failed before opening a session with `windows sandbox failed: helper_unknown_error: setup refresh had errors`; resetting its kernel did not repair it. Share links, protection bypass tokens and extracted browser credentials were not used. Owner confirmation of the existing authenticated dashboard/data is pending; direct authenticated baseline and post-update acceptance have not run.

The existing allowlisted packager successfully staged42 files,570054 bytes, from source head `90f7e8e962d026b0a3f8054de0d176b3744c0131`. Every copied source file matched the checkout; generated container configuration requires cloud persistence and uses temporary disk only for scratch. Manifest SHA-256: `0c417acaa094ddfc31a7f44c56b199fcf313560924e17232b4ac86d349939b3d`. The package and manifest remain local and ignored; packaging is not a new remote build or deployment. Review-store logical preservation was checked again and passed. Already completed application/PostgreSQL/browser suites were not repeated for this documentation-only follow-up.

Access recovery passes, but the authorized update has not been deployed because authenticated baseline/owner/data preservation must precede deployment. No replacement project/database, alias/environment/protection change, paid service, Production deployment, private-report upload, owner reset, accepted-live-data mutation or PR merge occurred. PR#1 stays Draft; previous commits/main are preserved. Hosted functional acceptance remains `BLOCKED` until authenticated checks are available.
