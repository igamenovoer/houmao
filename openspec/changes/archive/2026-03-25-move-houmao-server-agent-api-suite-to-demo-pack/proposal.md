## Why

The current canonical direct `houmao-server` managed-agent API validation flow lives under `tests/manual/`, which makes it behave like an ad hoc manual test harness instead of a self-contained operator tutorial and demo pack. We now need that workflow to match the repository's newer `scripts/demo/` pattern so maintainers can run it stepwise, drive one canonical unattended path end to end, and verify sanitized golden outputs without depending on test-only structure.

For HTT-style maintenance, the move also needs a stable non-interactive runner contract. Simply relocating the suite into `scripts/demo/` would still leave the repository without a dedicated harness, explicit fail-fast preflight, or reviewable design-phase case plans for the automatic and interactive validation paths.

## What Changes

- Replace the canonical `houmao-server` managed-agent API live validation entrypoint with a self-contained demo pack under `scripts/demo/`.
- Move the four-lane direct managed-agent API workflow into a pack-owned tutorial/demo surface with explicit `start`, `inspect`, `prompt`, `interrupt`, `verify`, and `stop` commands plus a canonical unattended `auto` path.
- Add a separate pack-local `autotest/run_autotest.sh --case <case-id>` harness for real-agent HTT execution, with an initial automatic case set of `real-agent-preflight`, `real-agent-all-lanes-auto`, and `real-agent-interrupt-recovery`.
- Add change-owned `testplans/case-*.md` design artifacts so the automatic scripts and the interactive companion guides are reviewed before implementation.
- Add pack-local tracked inputs, expected-report snapshots, sanitization and verification helpers, and pack-owned native agent-definition assets instead of depending on `tests/manual/` and test-fixture-only layout.
- Add a pack-local real-agent autotest harness for opt-in HTT validation of the direct `houmao-server` API workflow.
- **BREAKING**: the old `tests/manual/manual_houmao_server_agent_api_live_suite.py` flow stops being the canonical operator contract; docs and workflow references move to the new demo pack.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `houmao-server-agent-api-live-suite`: redefine the canonical direct `houmao-server` managed-agent API validation workflow as a `scripts/demo/` tutorial/demo pack with interactive, unattended, and autotest validation surfaces instead of a `tests/manual/` suite.

## Impact

- Affected code: `tests/manual/`, new `scripts/demo/houmao-server-agent-api-demo-pack/`, and likely a new or expanded `src/houmao/demo/...` helper package.
- Affected planning/docs: reference docs for the current live suite, new change-owned `testplans/`, and any docs that point operators at `tests/manual/`.
- Affected workflows: maintainer validation, canonical unattended `auto` verification, and real-agent HTT coverage for direct `houmao-server` managed-agent API behavior.
