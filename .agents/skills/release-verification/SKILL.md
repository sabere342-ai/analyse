---
name: release-verification
description: Verify a Madrid Retail Intelligence development phase before completion or release acceptance. Use for scope review, test evidence, source reconciliation, regression, typing, lint, privacy and security quality gates.
---

# Phase and release verification

1. Read the current delivery plan and its acceptance criteria, [test strategy](../../../docs/VERIFICATION.md) and current verification log. Verify work stays within the current user authorization.
2. Inspect actual manifests/scripts; choose relevant existing test, type/lint/build and regression commands. Do not invent commands or add trivial passing tests to fill gaps.
3. Execute checks in documented directories, preserve exit status and current-run results. Record test counts and separate passed/failed/skipped/expected-failure/unrun. A zero-test suite is not validation.
4. For imports, inspect row/source-total reconciliation, duplicate/overlap handling and rollback. For finance, verify Decimal/semantics/missing-data gates. For UI/export, exercise representative flows, RTL and safe text handling.
5. Check tracked/untracked changes, secrets/private report/database leakage, unsafe parser/export inputs, dependencies/licenses and applicable auth/backup controls. Never alter history or deploy to hide an issue.
6. Update documentation/evidence and report exact remaining risks. Block DONE for unmet acceptance, critical corruption, silent financial errors or high security issues. Continue through the authorized delivery scope; report external blockers only after independent work is complete.

## Required verification

Use `git diff --check` and `git status --short`; inspect full diff plus new file contents. Confirm evidence references real executions/current targets. State explicitly which relevant checks could not run and why. No pushes/deployments are authorized by this skill.
