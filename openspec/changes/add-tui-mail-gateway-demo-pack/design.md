## Context

The repository already has adjacent demo assets that cover parts of the desired story, but not the exact one the user wants:

- `gateway-mail-wakeup-demo-pack` shows a single mailbox-enabled session being awakened by gateway unread-mail polling.
- `cao-interactive-full-pipeline-demo` shows how to launch and inspect one live Claude or Codex TUI session through `cao_rest`.
- `mail-ping-pong-gateway-demo-pack` shows multi-turn mailbox wake-up, but only for managed headless participants rather than a visible TUI session.

The missing path is a narrow maintainer demo for one live TUI agent that repeatedly:

1. receives one filesystem-backed email injected by a harness,
2. is awakened by the gateway notifier,
3. reads and processes the nominated unread message through the gateway mailbox facade,
4. prints a short acknowledgment in the visible chat surface, and
5. marks that same message read before the next harness-driven injection.

The platform primitives already exist:

- `realm_controller build-brain`
- `realm_controller start-session --backend cao_rest --mailbox-*`
- `realm_controller attach-gateway`
- live gateway mailbox routes at `/v1/mail/*`
- gateway mail-notifier state plus durable notifier audit history
- copied dummy-project and lightweight `mailbox-demo` fixtures
- interactive TUI inspection helpers and tmux-backed session visibility

This change therefore does not need new mailbox or gateway primitives. It needs a new demo pack that composes the existing CAO, runtime, gateway, mailbox, and inspection surfaces into one reproducible three-turn workflow.

## Goals / Non-Goals

**Goals:**

- Add a standalone demo pack at `scripts/demo/tui-mail-gateway-demo-pack/`.
- Demonstrate one mailbox-enabled TUI session at a time, with the operator selecting `claude` or `codex` for the run.
- Reuse the tracked copied dummy-project and lightweight `mailbox-demo` fixture family instead of inventing a new project or heavyweight role family.
- Implement a harness-driven loop that injects one new message every five seconds only when the mailbox currently has no unread mail and fewer than three processed turns have completed.
- Make the demo observable through stable mailbox and gateway artifacts plus bounded human-review TUI evidence.
- Keep all demo-owned generated state under one selected output root.
- Support both an automatic path and a stepwise maintainer path.

**Non-Goals:**

- Launch Claude and Codex concurrently in one live run.
- Introduce `houmao-server` as an extra orchestration layer for this demo.
- Add new gateway protocol routes or mailbox transport features.
- Verify exact assistant wording from the TUI transcript.
- Replace or broaden the existing gateway wake-up or interactive CAO demo packs.

## Decisions

### Decision: Build a new standalone demo pack that combines the gateway wake-up and interactive TUI patterns

The pack should teach one coherent story. Extending an existing pack would inherit the wrong operator contract:

- `gateway-mail-wakeup-demo-pack` is intentionally single-message and focused on durable notifier audit, not repeated TUI observation.
- `cao-interactive-full-pipeline-demo` is intentionally prompt-driven, not mailbox-driven.
- `mail-ping-pong-gateway-demo-pack` is intentionally headless-first and two-agent.

The new pack will therefore own:

- `README.md`
- `run_demo.sh`
- tracked inputs
- `expected_report/report.json`
- pack-local wrapper scripts
- a backing module under `src/houmao/demo/tui_mail_gateway_demo_pack/`

The backing module should stay close to the newer thin-wrapper pattern and expose, at minimum:

- `driver.py` for command routing
- `models.py` for persisted state and report payloads
- `runtime.py` for CAO-backed TUI session startup and teardown
- `mailbox.py` for harness delivery and unread-state inspection helpers
- `reporting.py` for inspect, sanitize, and verify flows

**Alternatives considered**

- Extend `gateway-mail-wakeup-demo-pack`: rejected because repeated TUI review would blur its narrow single-wakeup teaching contract.
- Extend `cao-interactive-full-pipeline-demo`: rejected because mailbox wake-up would become an incidental add-on instead of the main contract.
- Extend `mail-ping-pong-gateway-demo-pack`: rejected because it teaches a different managed-headless, two-agent authority model.

### Decision: Use one CAO-backed mailbox-enabled TUI session per run, selected explicitly by `--tool`

The user wants the same demo story for Claude Code and Codex, but the demo itself is still single-agent. The cleanest operator contract is:

- `--tool claude` starts one Claude TUI run
- `--tool codex` starts one Codex TUI run

The pack will require explicit tool selection for `start` and `auto`, then persist that selection in `control/demo_state.json` so later `drive`, `inspect`, `verify`, and `stop` commands target the same session without repeating tool flags.

This avoids two common failure modes:

- hiding tool selection behind an arbitrary default when the whole point is Claude/Codex parity
- overcomplicating the demo by running both tools concurrently when only one mailbox queue is being demonstrated

**Alternatives considered**

- Default to Claude when `--tool` is omitted: rejected because it hides the most important operator choice.
- Launch both tools in one run: rejected because it turns a single-agent wake-up demo into a coordination demo.

### Decision: Reuse the existing `mailbox-demo` fixture family directly

The tracked `mailbox-demo` role already biases the agent toward one bounded mailbox task inside a copied dummy project, which is exactly the posture this demo needs. The mail body can carry the turn-specific instruction to acknowledge the message in chat and then mark it read.

The pack will therefore reuse:

- dummy project: `tests/fixtures/dummy-projects/mailbox-demo-python`
- Claude blueprint or recipe path rooted in `mailbox-demo-default`
- Codex blueprint or recipe path rooted in `mailbox-demo-default`

No new role package is required in v1 unless implementation proves that the existing bounded mailbox role is still too broad for stable demo behavior.

**Alternatives considered**

- Add a dedicated demo-specific role immediately: rejected because it expands fixture surface before proving the existing narrow role is insufficient.
- Reuse heavyweight GPU-oriented fixtures: rejected because they would distract from the mailbox task and make the demo slower and noisier.

### Decision: Keep startup on the runtime CLI plus loopback gateway, not on `houmao-server`

This demo is about one visible TUI session. The most direct authority model is the same one already used by the interactive CAO and gateway wake-up flows:

1. `build-brain`
2. `start-session --backend cao_rest --mailbox-transport filesystem`
3. `attach-gateway`
4. `PUT /v1/mail-notifier`

The pack should therefore follow the launcher-managed loopback CAO pattern and persist the resulting runtime manifest, gateway metadata, and mailbox binding under its own output root.

This preserves direct TUI observability through tmux while still using the same live gateway mailbox facade and notifier audit surface as the existing wake-up pack.

**Alternatives considered**

- Use `houmao-server`: rejected because it adds a second control plane without improving the single-agent TUI teaching story.
- Drive mailbox behavior through direct `mail check` CLI turns instead of the gateway notifier: rejected because later wake-up is the point of the demo.

### Decision: Use a harness-owned five-second tick loop with unread-zero gating and an idle-state safety check

The harness contract should match the user’s requested cadence:

- every five seconds, inspect whether the mailbox has unread mail
- if unread count is zero and fewer than three turns have completed, inject the next message

The pack should add one safety gate beyond that user-visible rule: only inject when the live gateway also reports `request_admission=open`, `active_execution=idle`, and `queue_depth=0`. That prevents the harness from injecting a new mail on a tick that happens after read state was updated but before the prior turn has really settled.

Each injected message will include:

- run id
- turn index (`1/3`, `2/3`, `3/3`)
- a short instruction to read the mail, acknowledge it in chat, and mark it read

The harness will deliver mail through the managed mailbox delivery boundary, not by mutating SQLite directly.

**Alternatives considered**

- Inject immediately when unread reaches zero: rejected because the user explicitly asked for a five-second harness cadence.
- Gate only on gateway idleness and ignore unread count: rejected because unread-zero is the simplest visible contract for this demo.
- Poll faster than five seconds: rejected because that changes the teaching contract and increases noise.

### Decision: Treat chat acknowledgment as human-review evidence, not as an exact golden-text contract

The visible TUI acknowledgment matters to the demo, but exact transcript text is too unstable to use as the main verification boundary across tools and runs.

The pack will therefore capture per-turn human-review evidence such as:

- a bounded tmux pane snapshot
- a best-effort projected output tail when available
- timestamps linking that evidence to the turn index and processed message id

Verification will assert that those artifacts exist and are associated with the completed turn, but it will not compare the exact assistant wording to a tracked snapshot.

The stable pass or fail contract will instead rely on:

- three injected messages
- three processed-message read transitions
- final unread count of zero
- notifier audit and queue evidence showing later wake-up work was enqueued

**Alternatives considered**

- Snapshot exact chat text: rejected because Claude and Codex TUI output wording is not stable enough.
- Ignore visible TUI evidence entirely: rejected because the user explicitly wants to see the agent print something in chat.

### Decision: Keep all generated state under one selected output root

The default output root should be pack-local and tool-specific so Claude and Codex runs do not collide:

- `scripts/demo/tui-mail-gateway-demo-pack/outputs/claude/`
- `scripts/demo/tui-mail-gateway-demo-pack/outputs/codex/`

At minimum, the selected output root will contain:

- `control/`
- `cao/`
- `runtime/`
- `mailbox/`
- `deliveries/`
- `project/`
- `evidence/`

The pack will redirect runtime, registry, mailbox, and job roots under that selected output root so the run remains self-contained and inspectable.

**Alternatives considered**

- Reuse ambient operator defaults for runtime or mailbox state: rejected because it breaks cleanup ownership and report reproducibility.
- Share one default output root across tools: rejected because it makes cross-tool reruns ambiguous.

## Risks / Trade-offs

- [Best-effort TUI text extraction can be noisy] → Treat projected output tails and tmux captures as human-review evidence only; keep the stable verification contract on gateway and mailbox artifacts.
- [Gateway notifier timing is inherently variable] → Verify stable outcome summaries and turn counts rather than exact poll-by-poll sequences.
- [Claude and Codex surface differences can affect inspection helpers] → Make tool selection explicit, store tool-specific metadata in persisted state, and test both tool paths with the same high-level contract.
- [A five-second cadence makes the live demo slower] → Keep the fixed cadence because it is the requested teaching contract, and rely on deterministic unit tests rather than fast live integration loops for most regression coverage.
- [The existing `mailbox-demo` role may still be too generic] → Reuse it first, but leave room to add a dedicated thin demo role if live behavior proves too broad.

## Migration Plan

This is an additive demo-pack change with no runtime or data migration requirement.

Implementation rollout:

1. add the pack-owned scripts, inputs, expected report, and backing module
2. add deterministic regression coverage for startup, drive-loop gating, inspection, and verification
3. document the operator workflow in the pack README

Rollback strategy:

- remove the new pack and backing module
- remove any pack-specific tests or fixture wiring added for the demo

## Open Questions

- None currently. If live implementation shows that `mailbox-demo` is too generic for a stable three-turn loop, the fallback is to introduce one thin dedicated demo role in the same change rather than redesign the pack authority model.
