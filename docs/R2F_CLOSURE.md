# R2-F functional closure — 2026-10-25

Verdict: `PARTIAL_MADRID_R2F_FUNCTIONAL_DELIVERY`. The worksheet defect is fixed and isolated PostgreSQL acceptance is proven. Real private POS acceptance and hosted acceptance remain unavailable; synthetic evidence does not replace them.

Recovered the clean existing branch `codex/madrid-r2-import-reliability` and Draft PR#1 at `b5e60cc36c70015681c64914bda3471dc41b72ab`; remote matched. Repository is `sabere342-ai/analyse`, main/base `a4c618c1f0fbfb902eb1692d687d5d9a87cdfd55`. Work continues in the same checkout/branch/PR, without resetting, cleaning or overwriting prior work. Final commit identity is bound by the updated PR head and delivery response.

| Defect | Root cause | Correction | Real verification |
| --- | --- | --- | --- |
| Last deselection silently meant all sheets | Empty list encoded both all and none | Explicit `all`/`selected` mode in UI and API; selected-empty and conflicting modes rejected | Chromium selected First only; backend stored only First; empty selection blocked |
| Reinspection discarded choices | Every inspection reset mapping and sheet state | Preserve same-source choices; invalidate old previews on parser/scope changes; full worksheet inventory separate from selected previews | Chromium reinspection retained selection/mapping; API included empty-sheet inventory |
| Wrong mapping could survive edits/source changes | Invalid JSON retained last valid mapping; asynchronous results lacked full source context | Reject invalid JSON shape, clear its parsed map, block submission; invalidate on file/type/parser changes and discard late responses | Invalid mapping blocked in Chromium; same-name/same-size stale-source regression |
| Inspection ignored selected sheets/profile | Endpoint forced all sheets and UI omitted PDF profile | Inspect with the same controlled options and selection; exact names validated | API inspection and staged details agree; missing names remain rejected |
| Manual dates could be overwritten | Inspection callback ignored the printed-date checkbox | Respect manual-date choice | Strict frontend build; private PDF journey remains unverified |
| Negative TLS case was Linux-specific | Removing test CA selected an absent `/etc` bundle on Windows | Test with an actual unrelated trust bundle and a mismatched hostname, retaining `verify-full` | Real PostgreSQL rejected both, without bypassing verification |
| Old reupload journey could pass without reuploading | Navigation remounted an empty file form but old accepted review remained | Test explicitly selects the identical file and checks the actual200/accepted response and unchanged batch count | Corrected Chromium journey passed |

Parser1.3.1/contract1.3.0 are versioned in new interpretations. Existing accepted batches are not rewritten. Legacy API requests without `sheet_mode` retain nonempty-list→selected/empty-list→all compatibility. New explicit selected-empty requests fail. Names preserve exact spaces; no implicit name repair or worksheet inclusion. Manual maps still require matching headings on every selected sheet; incompatible headings require separate imports.

## Functional input matrix

| Source | Inspection | Parsing | Reconciliation | Acceptance | Analysis | CSV/XLSX/PDF export |
| --- | --- | --- | --- | --- | --- | --- |
| Synthetic unknown CSV | PASS | PASS | PASS | PASS | PASS | PASS |
| Synthetic selected XLSX, different sheet headings | PASS | PASS | PASS | PASS | PASS | PASS |
| Synthetic legacy XLS | NOT_RUN | PASS | PASS | NOT_RUN | NOT_RUN | NOT_RUN |
| Synthetic multi-page table PDF | NOT_RUN | PASS | PASS | NOT_RUN | NOT_RUN | NOT_RUN |
| Actual inventory snapshot PDF | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| Actual representative-sales PDF | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| Actual warehouse-movement PDF | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| Scanned PDF/OCR | UNSUPPORTED | UNSUPPORTED | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |

`NOT_RUN_PRIVATE_SOURCE_UNAVAILABLE`: a bounded exact-name search covered this project's parent directory, ignored project/private/cache locations and the known Codex attachment location. None of the three named reports or associated `acceptance.json` was present. No unrelated personal directories/drives/projects were searched. No substitute was represented as a real report.

## Isolated PostgreSQL and Windows acceptance

Reused installed PostgreSQL18.4 binaries without downloads or changes to the existing running PostgreSQL service. Created one separate disposable cluster under ignored project cache, bound to loopback on its own port,16MiB shared buffers/16 connections. Fresh measurement before startup:1375MiB available RAM. Credentials/private keys stayed in ignored local state, never command values or public artifacts. The temporary CA was scoped only to test processes; no global trust change. TLS1.3, full certificate and hostname verification were exercised; unrelated CA and wrong hostname were rejected.

All **nine PostgreSQL cases executed**, with zero PostgreSQL skips: original/batch durability, selected workbook persistence, concurrent overlap exclusion, audited retention, cross-instance throttle, encrypted cloud backup/local restore, owner preservation, TLS rejection and the new explicit001→002 migration case. The migration case applies001 on a fresh isolated schema, creates synthetic owner/session state, upgrades the same schema to002, preserves authentication, proves database transaction rollback and then imports/accepts data. Other cases prove shared original storage and cross-instance sessions/analytics.

A separate actual HTTP server plus Chromium imported only First from a synthetic two-sheet workbook with different headings, mapped columns, reconciled/accepted, showed stock2 rather than101, and downloaded matching CSV/XLSX/PDF. Unselected barcode was absent from CSV. Source bytes/checksum were verified in PostgreSQL. After stopping/restarting the server, normalized rows, owner hash, existing session and throttle attempts persisted exactly. Missing profit remained unavailable. Repeatable-read encrypted backup restored exact rows into a new local destination with sessions invalidated; audited rollback removed contribution. Browser errors were absent and mobile had no page overflow. All schemas/data used here were synthetic and isolated; only owned test schemas were dropped. The owned cluster was stopped; the pre-existing PostgreSQL service remains running.

Current local review instance at `http://127.0.0.1:8000` was restarted on its same `.cache/r2-local-runtime` directory. All logical database tables were hash-compared before/after restart; health/root200 and existing owner-uninitialized state remain. No password or demonstration data was inserted into that review store.

## Executed final checks

Commands used existing Python3.12.15, Node24.19.0, installed Chromium and previously checksum-verified WeasyPrint70.0 DLLs. No dependencies were reinstalled or changed. The ignored PostgreSQL runner supplies only the isolated test URL/CA to its subprocess; no live Neon connection was used.

| Command | Exit | Result |
| --- | --- | --- |
| `.venv/Scripts/python.exe .cache/r2f_pg.py run -m pytest -q --tb=short -ra` |0|103 passed,7 explicit private-source skips; all9 PostgreSQL cases ran |
| `npm --prefix frontend run build` |0| Strict TypeScript/Vite production build |
| `npm --prefix frontend test` |0|13 passed, including source race and selection/mapping regressions |
| `npm --prefix frontend run format:check` |0| Passed |
| `.venv/Scripts/ruff.exe check madrid migrations tests` |0| Passed |
| `.venv/Scripts/ruff.exe format --check madrid migrations tests` |0| Passed |
| `.venv/Scripts/mypy.exe madrid` |0|14 source files checked |
| `npm --prefix frontend run e2e` |1|4 passed; old reupload test waited on an empty remounted form |
| `npm --prefix frontend run e2e -- --grep 'owner reviews import'` |0|Corrected failed journey passed, including actual idempotent reupload, exports, rollback and mobile;31.1s |
| `.venv/Scripts/python.exe .cache/r2f_pg.py run .cache/r2f_cloud_smoke.py` |0|PostgreSQL-backed Chromium imports/exports, actual restart, session/owner/throttle persistence, encrypted restore and rollback |
| `git diff --check` |0| Passed |

All five browser journeys have successful evidence: four from the final combined run and the corrected failed journey from its focused rerun. A new all-five aggregate exit0 run is not claimed. Initial selection regression failed before the fix. Infrastructure/browser helpers also needed output capture/base-URL repairs; those failed attempts were not counted as passes. The substantive TLS test failure and corrected trust/hostname rejection are described above. No repeated unchanged green suites were used to inflate evidence. Remote CI was not triggered or claimed.

## Vercel and preservation

`BLOCKED_VERCEL_403_ACCESS`: authenticated connector identity is `h99624697-8296`; team listing returns no authorized teams and `GET /v9/projects/madrid-retail-intelligence?teamId=team_Mxb8xgtqsSPG0KLkh7l9qZv5` returns403, requiring a team grant. CLI is authenticated as a different identity, `sabere342-9142`, and cannot resolve that scope. This is credential/team authorization evidence, not an application parser defect or proof of changed hosting configuration. Owner action: open a fresh connector `authorize_team_access` consent link, approve this existing team and complete SSO if requested. No global login/scope was changed, no SSO bypass or protection removal was attempted.

Access was not restored; no deployment/alias/environment/plan/database change occurred. No remote owner/data audit or hosted functional acceptance is claimed. The stable personal Preview, Hobby/free constraints, existing owner/password/sessions/accepted reports/audit/Neon configuration were never written to. No private reports or credentials were committed/uploaded, no paid resource was activated, main was not updated, PR#1 remains Draft and unmerged. Remaining gates are actual private-source acceptance and authorized hosted access/acceptance; scanned/unknown nested layouts retain their existing limitations.
