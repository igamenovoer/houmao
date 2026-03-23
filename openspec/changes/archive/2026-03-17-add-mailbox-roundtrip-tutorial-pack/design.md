## Context

The repository already documents the filesystem mailbox transport, runtime-owned mailbox commands, and tutorial-pack patterns, but those pieces are not yet combined into one reproducible mailbox roundtrip tutorial. Operators can infer the workflow from the mailbox reference docs and `realm_controller` CLI, yet there is no tracked pack that shows two agents joining the same mailbox root, exchanging a message via external control, and verifying the roundtrip with sanitized expected output.

Two existing repo patterns shape this work:

- Mailbox sessions are attached through `start-session`, which bootstraps the mailbox root, registers the session address, projects runtime-owned mailbox skills, and persists redacted mailbox bindings for later resume.
- Tutorial packs in this repository live under `scripts/demo/` and pair a step-by-step README with a one-click `run_demo.sh`, tracked inputs, and expected-report verification.
- CAO-backed interactive demos are the current product focus for TUI-oriented agents, so the new pack needs to exercise two concurrent `cao_rest` sessions instead of taking a headless-only shortcut.

The current interactive CAO demo is not a good direct fit because it is built around one long-running session plus demo-specific state machinery. This mailbox tutorial still needs the CAO-backed runtime path, but it needs two concurrent sessions and a report centered on runtime `mail` operations rather than prompt/control-input turns.

## Goals / Non-Goals

**Goals:**
- Add a self-contained tutorial pack under `scripts/demo/` for a two-agent mailbox roundtrip workflow.
- Demonstrate the supported external-control path: build/start two sessions, send mail, check mail, reply, check again, and stop both sessions.
- Keep the tutorial transparent by documenting the underlying commands explicitly in the README, while still providing `run_demo.sh` for one-click execution and snapshot refresh.
- Produce a sanitized expected report that captures the important structured outputs without hardcoding timestamps, absolute paths, or transient message identifiers.

**Non-Goals:**
- Introduce new mailbox transports, mailbox RPC surfaces, or mailbox protocol changes.
- Teach direct use of `rules/scripts/*.py` as the primary operator workflow.
- Generalize the existing interactive CAO demo into a reusable multi-agent framework.
- Require backward-compatible support for superseded demo patterns if a cleaner tutorial-pack structure is better for this repository.

## Decisions

### 1. The tutorial pack will live under `scripts/demo/` and follow the repo's existing tutorial-pack shape

The new pack will live under a new `scripts/demo/<pack-name>/` directory and will include `README.md`, `run_demo.sh`, tracked `inputs/`, `expected_report/report.json`, and helper scripts for sanitization and verification.

Why:
- Existing repo-local tutorial packs already live under `scripts/demo/`.
- The docs index already points readers to tutorial packs in that subtree.
- Reusing the local convention makes the new pack easier to discover and maintain than introducing a parallel `docs/tutorial/` layout in this repository.

Alternatives considered:
- Put the pack under `docs/tutorial/`.
  Rejected because the current repository convention for runnable tutorial packs is `scripts/demo/`, and this change benefits from staying consistent with the existing verification and snapshot patterns.

### 2. The implementation will stay tutorial-pack-local instead of introducing a generalized multi-agent demo framework

The primary orchestration will live in `run_demo.sh`, with small Python helpers for report sanitization and verification. If implementation needs structured parsing helpers, they will remain scoped to the tutorial pack rather than becoming a new generalized demo package by default.

Why:
- The mailbox roundtrip flow is linear and easy to explain as shell-visible steps.
- Keeping the logic local makes the README easier to mirror precisely.
- A general multi-agent demo framework would add design surface area that is not needed to satisfy this tutorial.

Alternatives considered:
- Build a new reusable `src/houmao/demo/...` package first.
  Rejected because it adds abstraction before the repository has more than one mailbox tutorial use case to justify it.

### 3. The tutorial will use CAO-backed sessions plus runtime-owned mailbox surfaces, not direct managed-script invocation

The pack will demonstrate mailbox usage through:

- `build-brain --blueprint`
- `start-session --blueprint --backend cao_rest`
- `mail send`
- `mail check`
- `mail reply`
- `stop-session`

The runner and README will treat mailbox-managed helpers under `rules/scripts/` as internal transport machinery rather than the operator-facing interface. Mailbox enablement itself will stay explicit in the `start-session` command through `--mailbox-transport`, `--mailbox-root`, `--mailbox-principal-id`, and `--mailbox-address` rather than through tutorial-specific mailbox recipe files.

Why:
- The mailbox docs explicitly position runtime `mail` commands as the operator workflow.
- `start-session` already handles mailbox bootstrap and registration.
- Current development focus is on CAO-backed TUI sessions, so the tutorial needs to exercise that path instead of a headless-only variant.
- Driving the demo through runtime surfaces exercises the supported integration path end to end.

Alternatives considered:
- Invoke `register_mailbox.py`, `deliver_message.py`, or `deregister_mailbox.py` directly.
  Rejected because that would bypass the runtime-owned workflow the docs are teaching and would demonstrate an internal helper surface instead of the intended user path.
- Use mailbox-enabled brain recipes for the tutorial pair.
  Rejected because no tracked recipe currently uses `mailbox`, and the tutorial is clearer when mailbox principal/address/root inputs remain visible in the `start-session` commands and `inputs/demo_parameters.json`.

### 4. The reply step will use the `message_id` returned by `mail send`

The tutorial will extract and validate a non-empty parent `message_id` from the `mail send` result before issuing `mail reply`. `mail check` remains part of the roundtrip as a visibility-confirmation step rather than the authority for reply-parent discovery.

Why:
- The runtime-owned parser validates core mailbox result fields, but the actual `message_id` still comes from the session-driven mailbox skill output rather than from a separate runtime-side schema guarantee.
- The documented `mail check` examples emphasize summary information like `unread_count`, not a guaranteed rich per-message listing.
- Using the send result removes ambiguity, but the runner must still fail clearly if `message_id` is absent instead of assuming it was produced.

Alternatives considered:
- Parse the parent message id from `mail check` output.
  Rejected because it would assume richer `check` payload content than the current public examples guarantee.

### 5. Tracked demo parameters will define a blueprint-driven CAO launch pair and the message content

The pack will use tracked inputs for the two launch configurations and the authored message bodies. The default tracked quick-start pair will be one Claude Code blueprint and one Codex blueprint, both meant for API-key-backed usage. The runner will copy those inputs into a temporary workspace and use them as the source of truth for the end-to-end flow.

Why:
- This keeps the pack self-contained and easy to reason about.
- It makes the README able to inline exact input content from tracked files.
- It keeps credential selection in the blueprint-bound recipes, where the current agent-definition model expects it.
- It minimizes `run_demo.sh` inputs for the common quick-start while still exercising two distinct blueprint/tool paths.

Alternatives considered:
- Hardcode all launch details in `run_demo.sh`.
  Rejected because tracked input files are easier to inspect, document, and snapshot alongside the tutorial.

### 6. The runner will keep local state minimal and rely on runtime-native recovery for live session lookup

The tutorial runner will use explicit agent identities plus captured `start-session` JSON artifacts for reporting and cleanup coordination, but it will not introduce a rich demo-owned `state.json` just to rediscover live CAO sessions later in the flow.

Why:
- The runtime already publishes tmux session environment that supports name-addressed recovery of manifest and agent-definition paths for follow-up control.
- This keeps the tutorial aligned with the native runtime contract instead of duplicating a second session-state source of truth.
- A smaller state surface keeps the linear tutorial easier to explain and less brittle.

Alternatives considered:
- Persist a tutorial-owned `state.json` with both sessions, manifests, and mailbox bindings.
  Rejected because it adds state-management machinery that the current linear flow does not need, and it would duplicate information the runtime already knows how to recover.

## Risks / Trade-offs

- [Concurrent session prerequisites may be stricter than single-session demos] → Mitigation: make prerequisites explicit, keep launch parameters tracked, and allow the demo to exit with a clear `SKIP:` path when required tools or credentials are unavailable.
- [Mailbox outputs contain many non-deterministic fields] → Mitigation: sanitize concrete runtime fields such as `message_id`, `thread_id`, `request_id`, `bindings_version`, absolute paths, runtime roots, and session manifests before expected-report comparison.
- [Two-session lifecycle cleanup is more failure-prone than single-session demos] → Mitigation: capture per-step outputs, install cleanup traps, stop both sessions in cleanup, and ensure partial-start failure still tears down whichever session already started.
- [README drift could turn the runner into a black box] → Mitigation: mirror each meaningful runner step in the README with explicit commands, inline critical inputs, and inline representative outputs.

## Migration Plan

No runtime or data migration is required. This change adds a new tutorial pack and its verification assets. If the repository surfaces tutorial links elsewhere, those links can be updated in the same change without compatibility shims.

## Open Questions

No blocking open questions. The change now fixes the v1 path as blueprint-driven, CAO-backed, mailbox-enabled through `start-session` overrides, and minimal-state by design.
