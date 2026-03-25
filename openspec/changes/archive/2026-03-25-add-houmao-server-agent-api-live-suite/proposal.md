## Why

The current `houmao-server` interactive demo path is workflow-oriented and has already proven too brittle to serve as the canonical live API verification surface for managed-agent creation and prompt control. We need a dedicated live suite that validates the public `houmao-server` agent APIs directly across both transports, without depending on demo-specific wrappers or gateway behavior.

## What Changes

- Add a dedicated operator-run live API suite that starts a real `houmao-server`, provisions isolated runtime roots, and exercises the public managed-agent routes directly over HTTP.
- Cover four real agent lanes in the first version: Claude TUI, Codex TUI, Claude headless, and Codex headless.
- Support both one all-lanes aggregate run and operator-selected per-lane runs from the same manual harness, with artifacts staged under a repo-local `tmp/` default run-root and an operator override path.
- Make the suite verify the full basic lifecycle for each lane: launch, managed-agent discovery, state inspection, prompt submission through `/houmao/agents/{agent_ref}/requests`, and stop.
- Keep the suite explicitly out of gateway scope for now so it validates direct server-owned agent creation and communication paths before layering gateway coverage on top.
- Use a dedicated lightweight `server-api-smoke` fixture family for the suite while reusing one copied lightweight dummy-project workdir so the suite is stable enough for repeatable live verification.

## Capabilities

### New Capabilities

- `houmao-server-agent-api-live-suite`: live, suite-owned verification of `houmao-server` startup plus TUI and headless managed-agent creation, status inspection, prompt submission, and stop behavior across Claude and Codex.

### Modified Capabilities

None.

## Impact

- Affected code: new live-suite harness and helpers under `tests/manual/` or equivalent suite-owned test paths, plus any shared helper modules needed to stage runtime homes, manifests, and isolated server roots
- Affected fixtures: lightweight tracked `server-api-smoke` blueprints/roles/recipes plus a copied lightweight dummy-project workdir used by the live suite
- Affected systems: `houmao-server`, CAO-compatible `/cao/*` creation routes for TUI lanes, `POST /houmao/launches/register`, and native headless `/houmao/agents/headless/launches`
- Dependencies: real local `tmux`, `claude`, and `codex` executables plus valid local credential material, with Codex exercised in API-key mode
