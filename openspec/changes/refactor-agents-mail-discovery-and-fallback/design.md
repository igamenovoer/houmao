## Context

The current mailbox stack has three overlapping agent-facing layers:

- gateway HTTP `/v1/mail/*` for attached sessions,
- `houmao-mgr agents mail ...` for managed-agent mailbox follow-up,
- projected mailbox skills that still tell agents to call `python -m houmao.agents.mailbox_runtime_support resolve-live` and, for filesystem mailboxes, inspect `rules/scripts/` before ordinary mailbox work.

That split leaves the hard part in the wrong place. The agent still has to learn mailbox discovery and filesystem protocol details each turn, and local `houmao-mgr agents mail ...` still routes ordinary `check`, `send`, and `reply` work through `_run_local_mail_prompt` instead of manager-owned direct execution.

An earlier unimplemented OpenSpec change proposed a top-level `houmao-mgr mail ...` family for current-session mailbox work. The current decisions reject that shape. Commands that depend on the notion of a current managed agent belong under `houmao-mgr agents ...`, and the ordinary workflow should be:

1. resolve live mailbox state through `houmao-mgr agents mail resolve-live`,
2. if a live gateway is available, use HTTP `/v1/mail/*`,
3. otherwise use `houmao-mgr agents mail ...`.

## Goals / Non-Goals

**Goals:**

- Provide a stable CLI discovery surface at `houmao-mgr agents mail resolve-live`.
- Keep all agent-scoped mailbox commands under `houmao-mgr agents mail ...`, with explicit-target and current-session-targeting behavior defined in one place.
- Replace local prompt-mediated mailbox follow-up with manager-owned direct execution for ordinary `status`, `check`, `send`, `reply`, and `mark-read`.
- Keep the agent workflow simple: gateway HTTP when live gateway is available, `houmao-mgr agents mail ...` otherwise.
- Reduce the filesystem mailbox public contract so mailbox `rules/` is markdown policy guidance rather than an executable protocol the agent has to relearn every turn.
- Allow thin skill-local shell wrappers where helpful, but make them wrappers over `houmao-mgr agents mail` and gateway HTTP rather than the canonical implementation.

**Non-Goals:**

- Redesign the mailbox data model, canonical message schema, or transport-specific storage layout.
- Remove gateway mailbox routes or replace the current loopback gateway model.
- Eliminate every compatibility helper script under `rules/scripts/` in the same change.
- Replace pair-managed `houmao-mgr agents mail ...` behavior for server-backed targets.
- Introduce a new top-level self-scoped `houmao-mgr mail` command family.

## Decisions

### 1. Make `houmao-mgr agents mail resolve-live` the public discovery contract

The supported discovery command for current mailbox work will be `houmao-mgr agents mail resolve-live`.

That command will resolve one managed agent mailbox context and return machine-readable discovery data including:

- mailbox transport,
- principal id and address,
- bindings version,
- whether live gateway mailbox routing is available,
- exact `gateway.base_url` when it is available.

Targeting rules:

- explicit `--agent-id` or `--agent-name` wins,
- otherwise, when the command runs inside the owning managed tmux session, it resolves the current agent from `AGENTSYS_MANIFEST_PATH`,
- if needed, it falls back to `AGENTSYS_AGENT_ID`,
- outside tmux with no explicit selector, it fails explicitly.

The command should support `--format json` and `--format shell` so projected skills can consume it directly or through thin shell helpers without depending on `jq`.

Alternatives considered:

- Keep `python -m houmao.agents.mailbox_runtime_support resolve-live` public.
  Rejected because it exposes a Python module path as the supported contract.
- Add `houmao-mgr mail resolve-live`.
  Rejected because current-session behavior belongs under `agents`, not at top level.
- Add `houmao-mgr agents self mail resolve-live`.
  Rejected because it adds a separate targeting subtree when `agents mail` can support both explicit selectors and current-session targeting clearly.

### 2. Keep all ordinary agent mailbox commands under `houmao-mgr agents mail`

The public CLI family for agent-scoped mailbox work will be:

- `houmao-mgr agents mail resolve-live`
- `houmao-mgr agents mail status`
- `houmao-mgr agents mail check`
- `houmao-mgr agents mail send`
- `houmao-mgr agents mail reply`
- `houmao-mgr agents mail mark-read`

This keeps mailbox discovery and follow-up alongside the rest of managed-agent control, and avoids a split where discovery lives under one command family while the actions live under another.

The same targeting rules apply across the family: explicit selectors when provided, otherwise same-session current-agent discovery inside tmux, otherwise explicit failure.

Alternatives considered:

- Introduce a top-level `houmao-mgr mail` family.
  Rejected because it hides the agent-scoped nature of the command and conflicts with the existing meaning of top-level `mailbox`.
- Keep discovery under `agents mail` but put fallback actions under a top-level `mail`.
  Rejected because it fragments one workflow into two command families for no gain.

### 3. Replace local prompt-mediated mailbox follow-up with manager-owned direct execution

Local-authority `houmao-mgr agents mail ...` commands should no longer prompt the target agent to interpret mailbox instructions for ordinary mailbox work. Instead, Houmao-owned code should perform direct mailbox execution for:

- mailbox status,
- mailbox check,
- mailbox send,
- mailbox reply,
- explicit mark-read.

This direct execution layer should reuse the same normalized request and response models used by the gateway mailbox facade where practical, so gateway and CLI behaviors stay aligned.

Pair-managed targets remain pair-owned: `houmao-mgr agents mail ...` continues to dispatch through the pair authority for those targets.

Alternatives considered:

- Keep local `check`, `send`, and `reply` on `_run_local_mail_prompt`.
  Rejected because it preserves the agent-learning problem and makes mailbox follow-up slower and less deterministic.
- Make direct CLI execution a local-only special path unrelated to gateway models.
  Rejected because it would create avoidable contract drift between gateway and CLI responses.

### 4. Keep gateway-first routing in the skill workflow, not inside the `houmao-mgr` fallback implementation

The supported skill workflow becomes:

1. call `houmao-mgr agents mail resolve-live`,
2. if live gateway mailbox routing is available, use HTTP `/v1/mail/check`, `/v1/mail/send`, `/v1/mail/reply`, and `/v1/mail/state`,
3. otherwise use `houmao-mgr agents mail check`, `send`, `reply`, and `mark-read`.

`houmao-mgr agents mail ...` itself should execute mailbox work directly rather than internally preferring gateway HTTP first. That keeps the CLI useful as the no-gateway fallback and avoids making gateway transport issues harder to debug.

Skill-local shell wrappers may exist, but only as thin dispatch helpers over this workflow.

Alternative considered:

- Make `houmao-mgr agents mail ...` prefer gateway HTTP automatically whenever a gateway is present.
  Rejected because it weakens the fallback boundary and makes the CLI less reliable when the gateway is the component under investigation.

### 5. Reframe filesystem `rules/` as mailbox-local policy, not the ordinary execution protocol

Filesystem mailbox `rules/` should remain part of the mailbox root, but its agent-facing role narrows to mailbox-local markdown guidance such as:

- formatting conventions,
- signature or subject conventions,
- mailbox-local etiquette,
- workflow hints.

Ordinary agent mailbox work should no longer require the agent to inspect `rules/scripts/requirements.txt`, invoke mailbox-owned Python helpers, or reason about `index.sqlite`, mailbox-local SQLite, lock files, or symlink projection details.

Houmao-owned code becomes responsible for transport-local protocol details in both gateway and direct manager execution paths.

Compatibility helper scripts may still exist under `rules/scripts/`, but they are no longer the ordinary public contract for agents or mailbox operators.

Alternatives considered:

- Keep `rules/scripts/` as the primary ordinary filesystem mailbox workflow.
  Rejected because it keeps protocol complexity in the wrong place and forces every agent turn to relearn mailbox mutation details.
- Remove `rules/` entirely.
  Rejected because mailbox-local policy and formatting guidance are still useful and should remain user-customizable.

### 6. Treat the earlier top-level `houmao-mgr mail` proposal as absorbed and replaced

This consolidated change absorbs and replaces the earlier unimplemented `refactor-agent-mailbox-to-houmao-mgr` proposal. The earlier proposal had the right simplification goal but the wrong command shape.

Implementation and docs should converge on the `houmao-mgr agents mail ...` family rather than splitting effort across both designs.

## Risks / Trade-offs

- `[Gateway and CLI drift]` -> Mitigate by sharing request and response models and one direct execution core between gateway and CLI paths where possible.
- `[Current-session targeting ambiguity]` -> Mitigate by using one explicit precedence order, failing clearly outside tmux without selectors, and documenting the exact discovery contract.
- `[Pair-managed versus local-managed divergence]` -> Mitigate by keeping the CLI response schema aligned across pair and local paths and limiting the difference to routing authority.
- `[Compatibility-script confusion during transition]` -> Mitigate by updating skill text and reference docs in the same change so `rules/scripts/` is no longer presented as the ordinary workflow.
- `[Mailbox policy versus protocol boundary drift]` -> Mitigate by documenting `rules/` as markdown policy and moving durable protocol rules into manager-owned code and formal specs.

## Migration Plan

1. Add `houmao-mgr agents mail resolve-live`, `mark-read`, and current-session targeting support to the `agents mail` family.
2. Extract or add a manager-owned direct mailbox execution layer and switch local `houmao-mgr agents mail ...` operations to use it.
3. Rewrite projected mailbox skills to use `houmao-mgr agents mail resolve-live`, gateway HTTP when available, and `houmao-mgr agents mail ...` fallback otherwise.
4. Update filesystem mailbox docs and contract surfaces so `rules/` is policy-oriented and `rules/scripts/` becomes compatibility or implementation detail.
5. Update mailbox reference docs and CLI reference docs to remove direct `python -m houmao...` discovery from the supported workflow.
6. Remove the earlier unimplemented top-level `houmao-mgr mail` proposal so only one mailbox refactor direction remains active.

No mailbox data migration is required. The change is about discovery, routing, and public contract boundaries rather than storage layout changes.

Rollback is straightforward because the message corpus, SQLite files, and mailbox registrations do not need to move:

- restore the old projected skill text,
- restore prompt-mediated local `agents mail` behavior,
- continue treating `rules/scripts/` as the ordinary agent workflow.

## Open Questions

- Should `houmao-mgr agents mail resolve-live --format shell` emit plain assignments or `export` statements that can be sourced directly?
- Should `resolve-live` include mailbox policy-path hints, or should projected skills discover mailbox-local markdown policy through path conventions after resolution?
- Should compatibility helper scripts under `rules/scripts/` remain published by default for debugging and repair, or become opt-in assets once manager-owned direct execution is complete?
