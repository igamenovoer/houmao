## Context

Houmao already has the pieces to inspect and control live tmux-backed agent sessions:

- tmux-backed runtime identity and control surfaces,
- CAO `shadow_only` parsing over exact `mode=full` terminal snapshots,
- managed raw control input through `send-keys`, and
- demo/test flows that persist reduced state or hand-written parser fixtures.

What the repository does not have is a repo-owned way to record a real running agent tmux session as durable test evidence. The missing piece is not just a screen capture. For state-tracking and parser regression work, we need a long-running recorder process that can target an already-running tmux session, preserve a human-reviewable terminal recording, preserve exact pane snapshots for machine replay, and describe when recorded input is authoritative versus best-effort.

There is one important tooling constraint in this repository: the supported `asciinema` surface is the repo-owned Pixi task backed by `extern/orphan/bin/asciinema-x86_64-unknown-linux-gnu`, not the conda package. The design therefore assumes `pixi run asciinema ...` as the canonical visual recorder surface.

## Goals / Non-Goals

**Goals:**
- Add a repo-owned recorder under `tools/terminal_record/` that targets an existing tmux session or pane.
- Support explicit `active` and `passive` recording modes with different capture guarantees.
- Persist synchronized artifacts that separate operator-facing visual recordings from replay-grade pane snapshots.
- Support long-running recorder lifecycle control with `start`, `status`, and `stop`.
- Make repo-owned managed `send-keys` recorder-aware when an `active` recorder targets the same tmux-backed session.
- Enable later analyze/replay/label workflows over recorded pane snapshots for parser and state-tracking tests.

**Non-Goals:**
- Do not guarantee capture of every arbitrary external manual input source in `passive` mode.
- Do not treat the `asciinema` cast as the authoritative parser replay surface.
- Do not redesign CAO runtime parsing, tmux runtime identity, or `send-prompt` prompt-turn semantics.
- Do not attempt full generic auditing of third-party `tmux send-keys` invocations executed outside repo-owned control paths.

## Decisions

### Decision 1: Use a long-running controller process with persisted live state

**Choice:** The recorder will run as a long-lived background controller process that owns one recorder run root and persists `live_state.json` or equivalent process metadata for later `status` and `stop` operations.

**Rationale:**
- The user explicitly wants launch-now, stop-later behavior against an already-running tmux session.
- A persisted control record is simpler and more robust than trying to reconstruct recorder state from tmux alone.
- This makes recorder lifecycle explicit and keeps preserved artifacts decoupled from whether the process is still live.

**Alternatives considered:**
- One-shot shell wrappers: rejected because they do not support durable `status`/`stop` control cleanly.
- Pure tmux-session discovery without recorder state: rejected because process, artifact, and mode metadata would be too implicit and fragile.

### Decision 2: Treat `active` and `passive` as different authority contracts, not just different UI modes

**Choice:** The recorder will expose `active` and `passive` as first-class mode contracts with explicit metadata describing capture authority.

In `active` mode, the recorder becomes the managed interactive path and can claim authoritative managed-input capture while that path remains intact.

In `passive` mode, the recorder observes output and exact pane state but does not claim complete manual input capture.

**Rationale:**
- tmux can reliably expose pane content, but it cannot passively guarantee a full log of all keys sent from arbitrary attached clients.
- Making the authority boundary explicit prevents downstream replay/tests from over-trusting passive recordings.
- This supports both workflows the user wants: authoritative controlled capture and unobtrusive observation.

**Alternatives considered:**
- A single mode with implicit best-effort semantics: rejected because it would blur testing guarantees.
- Claiming full input capture in passive mode: rejected because the underlying transport does not justify that promise.

### Decision 3: Split visual capture from replay-grade snapshot capture

**Choice:** Each run will persist both:
- an `asciinema` cast for human review, and
- a time-ordered tmux pane snapshot stream as the machine replay surface.

The pane snapshot stream, not the cast, will be the authoritative source for parser and state replay.

**Rationale:**
- Current parser/runtime behavior consumes exact terminal snapshots (`tmux capture-pane` / CAO `mode=full`), not terminal player reconstructions.
- The cast remains valuable for human inspection, debugging, and sharing, but it should not drive automated parser/state assertions.
- This lets replay work without requiring a live tmux session or cast re-rendering.

**Alternatives considered:**
- Use only `asciinema` casts: rejected because parser/state replay would depend on reconstructing pane state from event streams.
- Use only pane snapshots: rejected because operators still need a readable visual artifact.

### Decision 4: Integrate recorder-aware managed input at repo-owned `send-keys` boundaries

**Choice:** When an `active` recorder targets a tmux-backed session, repo-owned managed control-input delivery will append recorder-visible input events as part of the existing `send-keys` path.

This integration stays narrow: it augments managed input that already flows through repo-owned runtime control, rather than attempting to intercept all possible external tmux input.

**Rationale:**
- `send-keys` is already the repo-owned raw control-input abstraction for these sessions.
- Recorder-aware logging there captures important non-manual input that matters for TUI state reproduction.
- Narrow integration reduces coupling and avoids pretending we can comprehensively audit third-party tmux commands.

**Alternatives considered:**
- Ignore managed `send-keys`: rejected because it would leave an important source of TUI state transitions unrecorded.
- Attempt global tmux interception of every input source: rejected as operationally brittle and outside the repo's current control boundary.

### Decision 5: Use a recorder-owned run root with exportable replay artifacts

**Choice:** The initial recorder writes run artifacts under a recorder-owned run root, expected under `tmp/terminal_record/<run-id>/`, and later analyze/export flows can turn selected runs into stable checked-in fixtures.

**Rationale:**
- Ad hoc recordings and curated fixtures have different lifecycles.
- Keeping raw captures out of checked-in fixtures by default reduces repo churn and accidental large artifacts.
- Export remains possible once a recording is labeled and worth preserving.

**Alternatives considered:**
- Write directly into `tests/fixtures/`: rejected because most recordings will be exploratory and not all should become checked-in fixtures.

## Risks / Trade-offs

- [Passive mode cannot guarantee full manual input capture] → Mitigation: persist explicit `input_capture_level` and taint metadata so downstream tooling can make safe decisions.
- [Recorder-aware `send-keys` adds coupling between tooling and runtime control paths] → Mitigation: keep the integration narrow and additive, leaving core prompt/control semantics unchanged.
- [Extra attached tmux clients can degrade active-mode guarantees] → Mitigation: record taint reasons, and prefer an exclusive-input policy for authoritative active runs.
- [Dual artifacts increase storage and operational complexity] → Mitigation: keep artifact formats simple, structured, and scoped to recorder-owned run roots with later export as an explicit step.
- [A long-running controller can leave stale state after crashes] → Mitigation: make `status` validate live process identity and allow recovery/finalization paths that preserve partial artifacts.

## Migration Plan

1. Add the recorder tool surface under `tools/terminal_record/` with run-root/state-file conventions and the `start`/`status`/`stop` lifecycle.
2. Add recorder artifact schemas and the dual-mode metadata contract.
3. Integrate exact tmux pane snapshot sampling and repo-owned `pixi run asciinema` visual capture.
4. Add recorder-aware managed `send-keys` logging for `active` recorder runs.
5. Add analyze/replay/label flows that consume recorded pane snapshots and produce replay-grade observations or exported fixtures.
6. Add tests for recorder control logic, artifact contracts, and recorder-aware control-input integration.

Rollback is straightforward because this change is additive: disable or remove the recorder tool and recorder-aware logging without requiring data migration in core runtime manifests. Preserved recorder runs can remain as inert artifacts on disk.

## Open Questions

- None blocking for proposal/design readiness. The remaining details are implementation-level choices such as exact file names, polling cadence defaults, and export workflow ergonomics.
