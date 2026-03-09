## Context

Current CAO demo scripts in `scripts/demo/` are primarily one-shot validation flows that launch, prompt once (or in a fixed sequence), verify, and tear down automatically. They are good for CI stability but not for hands-on runtime inspection because operators cannot reliably keep a session alive while iteratively sending prompts and observing tmux output in real time. The requested change introduces a deterministic interactive pipeline for CAO-backed Claude sessions with explicit lifecycle boundaries.

## Goals / Non-Goals

**Goals:**
- Provide a repeatable local interactive demo that starts a CAO-backed Claude session and keeps it alive for manual inspection until the user intentionally stops it.
- Make session state discoverable by emitting stable metadata needed for `tmux attach`, terminal-log tailing, and subsequent name-based `send-prompt` / `stop-session` calls.
- Support multi-turn prompt driving against one session identity with simple command surfaces suitable for manual and scripted usage.
- Preserve existing CI-friendly demo behavior by isolating this interactive flow instead of changing current one-shot demos.

**Non-Goals:**
- Replacing all existing demo scripts with interactive behavior.
- Introducing remote/non-local tmux control semantics beyond existing local constraints.
- Defining a new runtime backend or changing CAO protocol contracts.

## Decisions

1. Add a dedicated interactive demo pack instead of modifying existing one-shot demos.
Rationale: Current demos are tuned for deterministic teardown and report verification. Mixing interactive persistence into them would increase complexity and flake risk for established flows.
Alternatives considered:
- Add a `--keep-session` flag to existing demo scripts: lower duplication but increases branching and testing matrix across multiple demos.
- Reuse `cao-claude-esc-interrupt` as-is: close behavior but purpose-built around Esc interruption, not generic turn-loop workflows.

2. Use explicit lifecycle commands (`start`, `send-turn`, `inspect`, `stop`) over one monolithic script.
Rationale: Interactive workflows are operator-driven; explicit subcommands avoid hidden teardown and make repeat runs predictable.
Alternatives considered:
- Single long-running script loop: simpler initial UX but harder to recover/debug after partial failures.

3. Persist session metadata in a workspace-local machine-readable state file.
Rationale: `send-prompt` and inspection steps need stable references (session identity, tmux target, terminal id/log path) across invocations.
Alternatives considered:
- Keep data in process memory only: incompatible with separate command invocations.
- Parse ad-hoc logs each time: fragile and harder to maintain.

4. Keep local-only CAO assumptions aligned with existing tmux-based demos.
Rationale: tmux inspection and key injection patterns are local host operations; enforcing local CAO base URL avoids ambiguous remote behavior.
Alternatives considered:
- Allow remote CAO endpoints: introduces uncertainty around terminal ownership/visibility and would need additional transport guarantees.

5. Fix the demo CAO base URL to `http://127.0.0.1:9889`.
Rationale: This workflow is intentionally single-path and local. Pinning the loopback target removes operator ambiguity, avoids override-specific branching, and keeps launcher behavior deterministic.
Alternatives considered:
- Accept arbitrary CAO base URL values: more flexible, but contrary to the demo's local-only goal and less predictable for tmux inspection.

6. Use name-based `--agent-identity` as the primary session handle.
Rationale: Current runtime already supports tmux-backed name identities for `start-session`, `send-prompt`, and `stop-session`. Keeping the demo operator-facing around one stable identity is simpler than forcing users to work from manifest paths.
Alternatives considered:
- Use `session_manifest` as the only resume handle: works, but is less ergonomic for a human-driven demo and does not match the intended interactive operator workflow.

7. `start` force-closes any previously active demo session before launching the replacement session.
Rationale: The demo is intended to operate one agent at a time. Replacing the previous session keeps the workflow simple and avoids making operators perform explicit cleanup before every restart.
Alternatives considered:
- Fail when active state exists: safer for general-purpose tooling, but adds friction to this demo-specific workflow.

## State Model

The interactive demo persists a workspace-local state artifact that is rewritten across `start`, `send-turn`, `inspect`, and `stop`.

Required state fields:

- `active`: whether the demo currently believes the session is active
- `agent_identity`: canonical tmux-backed name used as the primary handle for `send-prompt` and `stop-session`
- `session_manifest`: persisted runtime manifest path retained for diagnostics
- `session_name`: resolved tmux / CAO session name
- `tmux_target`: attach target shown to operators
- `terminal_id`: CAO terminal identifier
- `terminal_log_path`: CAO terminal log path
- `runtime_root`: runtime root used for generated artifacts
- `workspace_dir`: demo workspace path
- `updated_at`: ISO-8601 UTC timestamp of the most recent state update

Lifecycle rules:

- `start` always targets `http://127.0.0.1:9889`.
- If existing state is marked active, `start` first attempts `brain_launch_runtime stop-session --agent-identity <previous-agent-identity>` and then replaces the state with the new session metadata.
- `send-turn` and `stop` use `agent_identity` as the primary targeting value.
- The previous state must not remain marked active after a successful replacement or stop.

## Risks / Trade-offs

- [Risk] Session leaks when users forget explicit stop.
  - Mitigation: `start` replaces an existing active session, `stop` remains available for explicit teardown, and command output should show which prior identity was replaced.
- [Risk] Ownership mismatch with untracked local CAO server process.
  - Mitigation: Reuse launcher ownership checks and retry pattern used by current CAO demos while always targeting `http://127.0.0.1:9889`.
- [Risk] Interactive timing variability may reduce deterministic assertions.
  - Mitigation: Keep verification focused on invariant outcomes (non-empty responses, same `agent_identity` across turns, accessible tmux target) instead of brittle timing conditions.
- [Trade-off] Additional script surface area to maintain.
  - Mitigation: Share helper logic and structure with existing CAO demo patterns where practical.
