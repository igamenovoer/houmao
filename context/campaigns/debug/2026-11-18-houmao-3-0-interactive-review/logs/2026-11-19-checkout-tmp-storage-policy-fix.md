# Checkout tmp Storage-Policy Fix

Date: 2026-11-19. Status: implemented; physical `tmp/` launch, signed gateway P1, full unit suite, lint, type checking, and documentation build verified.

## Request and Scope

The operator required all generated test materials to reside physically under `tmp/<subdir>/` and then explicitly requested a code fix after the fixture and gateway restrictions were identified. This was a separate support change, not a silent modification during a diagnostic run.

The change permits private run and gateway access state only in purpose-specific subdirectories of a checkout's `tmp/` tree. Other checkout paths remain rejected. Reusable fixture auth stores and credential env files remain external, symlink components remain forbidden for gateway access, owner-only permissions remain required, and nested worktree markers still reject storage.

## Implementation

- `scripts/agents/test-fixtures/fixturelib/auth.py` adds an optional checkout-`tmp` allowance for run roots. It rejects the bare `tmp/` root and all non-`tmp` checkout paths. Auth roots keep the original external-only policy.
- `scripts/agents/test-fixtures/fixturelib/prepare.py` applies the same run-path rule when loading prepared state.
- `src/houmao/gateway/_access_storage.py` carries the lexical destination through no-follow directory traversal. A `.git` marker now rejects the destination unless it remains in a purpose-specific subdirectory of that worktree's `tmp/` root. A nested `.git` marker still rejects storage.
- Focused tests cover allowed run roots, rejected auth and other checkout roots, allowed gateway files under `tmp/<purpose>/`, rejection of files directly under `tmp/`, and rejection after a nested worktree marker appears.
- `scripts/agents/test-fixtures/README.md`, gateway access documentation, contributor guidance, and campaign documents were updated to describe the new rule.

## Focused Verification

The initial boundary test command was:

```bash
pixi run pytest -q \
  tests/unit/agents/test_agent_fixture_tools.py::test_run_root_allows_only_purpose_specific_checkout_tmp \
  tests/unit/agents/test_agent_fixture_tools.py::test_private_roots_respect_xdg_and_reject_checkout_symlinks \
  tests/unit/gateway/test_access.py::test_private_source_allows_only_purpose_specific_checkout_tmp \
  tests/unit/gateway/test_access.py::test_private_source_rejects_shared_symlink_checkout_and_oversize
```

Result: **5 passed in 0.14s**.

The broader verification then passed:

- `pixi run pytest -q tests/unit/agents/test_agent_fixture_tools.py tests/unit/agents/test_dsh_fixture_tools.py tests/unit/gateway/test_access.py`: **139 passed in 21.52s**.
- `pixi run typecheck`: strict mypy reported no issues in **520 source files**.
- `pixi run lint`: full Ruff lint passed.
- `pixi run test`: **4,946 passed, 14 skipped** in 79.64s.
- `pixi run docs-build`: strict MkDocs build succeeded.

## Physical Relocation

The earlier external preparation `self-hosted-dsh-headless-manager-93aaf19e0759` was never launched. Instead of rewriting credential-bearing absolute paths, the fixed fixture created a fresh replacement directly in the checkout's ignored scratch tree:

```text
/data/huangzhe/code/houmao/tmp/houmao-30-iter2-rc3/runs/self-hosted-dsh-headless-manager-4098c41338ef
```

The new run's `run.json` contains only that physical `tmp/` run path and its descendants. `fixture.py check --run-dir <new-run>` returned `status: prepared` with `prerequisites.missing: []`. The superseded external campaign root `/home/huangzhe/.local/state/houmao-30-iter2-rc3/` was then removed. The current `tmp/houmao-30-iter2-rc3/` is a real directory, not a symlink.

The shared role is physically located at `tmp/houmao-30-iter2-rc3/inputs/iter2_dsh_system_prompt.txt`. No RC1/RC2 diagnostic state was moved or deleted.

## Live Launch and P1 Verification

The fixed fixture launched the physical `tmp/` run and submitted P1 through its authenticated gateway. This exercised private gateway state creation and owner-local signed usage reads, not only the isolated path-policy tests.

- Agent ID: `fd4e2343-7ed5-4346-8105-a645933fde83`.
- Runtime session: `dsh_headless-20261119-103743Z-2b2c438d`.
- tmux session: `HOUMAO-self-hosted-dsh-headless-manager-4098c41338ef-1795084663404`.
- Gateway: `http://127.0.0.1:38605` in detached-process mode.
- Native session: `session-5b3b8aa7-7390-4245-bcda-d8183c4cd968`.
- Turn: `turn-2d66cb64e363`, outcome `completed`, with 6,776 input tokens, 10 output tokens, and 6,786 total tokens.
- Live `fixture.py check --run-dir <run> --live` returned `live_requested: true`, no missing prerequisites, and healthy usage collection.
- The captured pane returned `{{ITER1_LITERAL}} $KEEP_LITERAL OK` followed by `[complete] native_completed`.

The agent remains running for P2–P4. The exact attach wrapper is `tmp/houmao-30-iter2-rc3/attach-h1.sh`; it is executable and passed `bash -n`. This completes the storage-policy fix and H1 P1, not the remaining H1 gate.
