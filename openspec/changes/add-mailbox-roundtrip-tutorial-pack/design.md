## Context

The repository already documents the filesystem mailbox transport, runtime-owned mailbox commands, and tutorial-pack patterns, but those pieces are not yet combined into one reproducible mailbox roundtrip tutorial. Operators can infer the workflow from the mailbox reference docs and `realm_controller` CLI, yet there is no tracked pack that shows two agents joining the same mailbox root, exchanging a message via external control, and verifying the roundtrip with sanitized expected output.

Two existing repo patterns shape this work:

- Mailbox sessions are attached through `start-session`, which bootstraps the mailbox root, registers the session address, projects runtime-owned mailbox skills, and persists redacted mailbox bindings for later resume.
- Tutorial packs in this repository live under `scripts/demo/` and pair a step-by-step README with a one-click `run_demo.sh`, tracked inputs, and expected-report verification.

The current interactive CAO demo is not a good direct fit because it is built around one long-running session plus demo-specific state machinery. This mailbox tutorial needs two concurrent sessions and a report centered on runtime `mail` operations rather than prompt/control-input turns.

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

### 3. The tutorial will use runtime-owned mailbox surfaces, not direct managed-script invocation

The pack will demonstrate mailbox usage through:

- `build-brain`
- `start-session`
- `mail send`
- `mail check`
- `mail reply`
- `stop-session`

The runner and README will treat mailbox-managed helpers under `rules/scripts/` as internal transport machinery rather than the operator-facing interface.

Why:
- The mailbox docs explicitly position runtime `mail` commands as the operator workflow.
- `start-session` already handles mailbox bootstrap and registration.
- Driving the demo through runtime surfaces exercises the supported integration path end to end.

Alternatives considered:
- Invoke `register_mailbox.py`, `deliver_message.py`, or `deregister_mailbox.py` directly.
  Rejected because that would bypass the runtime-owned workflow the docs are teaching and would demonstrate an internal helper surface instead of the intended user path.

### 4. The reply step will use the `message_id` returned by `mail send`

The tutorial will record the parent `message_id` from the `mail send` result and feed that identifier into the later `mail reply` step. `mail check` remains part of the roundtrip as a visibility-confirmation step rather than the authority for reply-parent discovery.

Why:
- The current documented `mail send` result contract already includes `message_id`.
- The documented `mail check` examples emphasize summary information like `unread_count`, not a guaranteed rich per-message listing.
- Using the send result removes ambiguity and keeps the tutorial tied to the strongest stable contract.

Alternatives considered:
- Parse the parent message id from `mail check` output.
  Rejected because it would assume richer `check` payload content than the current public examples guarantee.

### 5. Tracked demo parameters will define the two-agent launch pair and message content

The pack will use tracked inputs for the two launch configurations and the authored message bodies. The runner will copy those inputs into a temporary workspace and use them as the source of truth for the end-to-end flow.

Why:
- This keeps the pack self-contained and easy to reason about.
- It makes the README able to inline exact input content from tracked files.
- It allows future adjustment of recipe selectors, roles, or identities without rewriting the runner logic.

Alternatives considered:
- Hardcode all launch details in `run_demo.sh`.
  Rejected because tracked input files are easier to inspect, document, and snapshot alongside the tutorial.

## Risks / Trade-offs

- [Concurrent session prerequisites may be stricter than single-session demos] → Mitigation: make prerequisites explicit, keep launch parameters tracked, and allow the demo to exit with a clear `SKIP:` path when required tools or credentials are unavailable.
- [Mailbox outputs contain many non-deterministic fields] → Mitigation: sanitize absolute paths, timestamps, runtime roots, session manifests, and message identifiers before expected-report comparison.
- [Two-session lifecycle cleanup is more failure-prone than single-session demos] → Mitigation: capture per-step outputs, stop both sessions in cleanup, and keep the final report focused on both success paths and cleanup outcomes.
- [README drift could turn the runner into a black box] → Mitigation: mirror each meaningful runner step in the README with explicit commands, inline critical inputs, and inline representative outputs.

## Migration Plan

No runtime or data migration is required. This change adds a new tutorial pack and its verification assets. If the repository surfaces tutorial links elsewhere, those links can be updated in the same change without compatibility shims.

## Open Questions

No blocking open questions. The implementation can finalize the default pair of tracked launch parameters as long as the pack remains self-contained, documents its prerequisites clearly, and preserves the runtime-owned mailbox workflow described above.
