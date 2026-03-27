## 1. Audit and sanitize tracked auth fixtures

- [x] 1.1 Inventory tracked auth files under `tests/fixtures/agents/` and `scripts/demo/**/agents/`, classifying each as removable credential payload, keepable placeholder, or keepable bootstrap template.
- [x] 1.2 Remove or sanitize tracked credential-bearing fixture files in the working tree so no tracked auth file contains live tokens, API keys, refresh tokens, or session exports.
- [x] 1.3 Update any fixture docs or comments that currently imply tracked real credentials are acceptable, replacing them with explicit placeholder or local-only guidance.

## 2. Harden ignore rules for repo credentials

- [x] 2.1 Update top-level `.gitignore` and any fixture-local ignore files so auth env files, `auth.json`, OAuth token payloads, and similar credential-bearing files under repo auth directories are ignored by default.
- [x] 2.2 Add targeted allowlist exceptions for tracked secret-free templates or placeholders that must remain versioned.
- [x] 2.3 Verify with `git check-ignore` and `git ls-files` that intended local credential files are ignored while approved placeholders remain trackable.

## 3. Rewrite reachable history and remote refs

- [x] 3.1 Create a backup ref, rewrite local history to remove the tracked Codex `auth.json` from reachable history, and verify the removed path is absent from the rewritten branch history.
- [x] 3.2 Inspect repo-owned branches and tags that new clones may fetch, then delete or move any remaining refs that still expose the leaked credential commit.
- [x] 3.3 Force-update the canonical remote branch to the sanitized history and confirm a fresh reachable-history inspection no longer surfaces the removed `auth.json`.

## 4. Verify repo credential hygiene

- [x] 4.1 Re-scan `tests/fixtures/agents/` and other tracked auth fixture trees for live-looking secrets, confirming only placeholders, empty stubs, or bootstrap templates remain tracked.
- [x] 4.2 Validate the OpenSpec change and record any collaborator follow-up required after the history rewrite, such as reclone or force-reset instructions.
