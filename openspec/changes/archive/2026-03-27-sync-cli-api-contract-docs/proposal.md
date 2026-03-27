## Why

Recent CLI, API-adjacent, and runtime contract updates are already implemented in code, but several operator-facing and reference docs still describe older behavior. That drift is now large enough to mislead readers about the supported `houmao-mgr` workflow, the live `houmao-server` flag surface, and the current gateway/mailbox/runtime control contracts.

## What Changes

- Refresh the getting-started path so it teaches the current managed-agent workflow based on `houmao-mgr agents launch --agents ... --agent-name ...`, prompt targeting by managed-agent selectors, and `agents stop` instead of older `--manifest`, `--session-id`, or `agents terminate` examples.
- Update CLI reference docs to match the live `houmao-server` and `houmao-mgr` command surfaces, including newer command families that are implemented but not yet formally documented.
- Correct stale runtime and subsystem reference pages so they match the current session-root versus job-dir model, legacy-backend retirement posture, raw control-input support, gateway attach targeting rules, and mailbox live-discovery guidance.
- Add dedicated CLI reference coverage for managed-agent gateway, turn, mail, mailbox, and cleanup workflows, then cross-link those pages from overview and API reference docs.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `docs-getting-started`: update getting-started guidance so the quickstart and overview reflect the current `houmao-mgr` operator workflow and current backend positioning.
- `docs-cli-reference`: expand CLI reference requirements so `houmao-server` and `houmao-mgr` pages reflect the live command and flag surfaces, including dedicated coverage for newer managed-agent command families.
- `docs-run-phase-reference`: update run-phase docs so session lifecycle, backend notes, and legacy-backend guidance match the current implementation and current public posture.
- `agents-reference-docs`: update runtime-managed agent reference requirements so control-surface, targeting, and lifecycle docs reflect current command names, raw control-input behavior, and manifest/session-root semantics.
- `agent-gateway-reference-docs`: update gateway reference requirements so current-session attach discovery, managed-agent gateway control surfaces, and `current-instance.json` authority are documented consistently.
- `mailbox-reference-docs`: update mailbox reference requirements so late mailbox registration, `resolve-live` endpoint discovery, and current shared mailbox workflows are documented accurately.

## Impact

- Affected docs: `docs/getting-started/`, `docs/reference/cli/`, `docs/reference/run-phase/`, `docs/reference/agents/`, `docs/reference/gateway/`, `docs/reference/mailbox/`, and related index/cross-link pages.
- Likely new reference pages: dedicated CLI pages for managed-agent gateway, turn, mail, mailbox, and cleanup workflows.
- Affected code surfaces used as documentation truth sources: `src/houmao/srv_ctrl/commands/`, `src/houmao/server/`, `src/houmao/agents/realm_controller/`, and `src/houmao/agents/mailbox_runtime_support.py`.
- Affected readers: operators and integrators who rely on repository docs for the supported CLI, API-adjacent behavior, and runtime contract details.
