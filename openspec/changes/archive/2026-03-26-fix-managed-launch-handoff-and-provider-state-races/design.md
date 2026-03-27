## Context

Two separate live failures in the local managed-agent workflow share one theme: control surfaces are doing the right high-level job but still carrying unsafe low-level assumptions.

For launch handoff, `houmao-mgr agents launch` successfully starts the runtime-owned tmux session and then unconditionally executes `tmux attach-session`. In non-interactive callers that have no real TTY, tmux reports `open terminal failed: not a terminal` even though the launch already succeeded. That makes a successful serverless launch look partially broken and bypasses the repo's libtmux-first tmux integration boundary.

For resumed local control, commands such as `agents state`, `agents gateway status`, and `agents gateway attach` all resolve the managed session through `resume_runtime_session()`. For unattended Claude sessions, that rebuild path re-applies launch-policy home mutations and rewrites `settings.json` plus `.claude.json`. Log injection proved that concurrent commands can interleave as: process A truncates `settings.json`, process B reads zero bytes, process B fails with `Malformed JSON state ... Expecting value`. The root problem is not Claude corruption; it is Houmao re-running start-time provider bootstrap on ordinary resumed control paths and writing those owned files non-atomically.

Constraints:

- keep unattended bootstrap for fresh-home provider start and relaunch
- keep interactive tmux handoff for real terminals
- use libtmux whenever practical for tmux operations
- prefer direct correctness fixes over compatibility shims

## Goals / Non-Goals

**Goals:**

- Let non-headless `houmao-mgr agents launch` succeed cleanly in non-interactive callers without a false tmux attach failure.
- Route launch handoff and tmux session resolution through the repo-owned libtmux-first tmux integration boundary whenever practical.
- Ensure read-only or already-live resumed control paths do not rewrite unattended provider bootstrap files.
- Ensure any remaining strategy-owned provider-state mutation is serialized and atomically committed so concurrent commands cannot observe partial files.
- Preserve existing fresh-launch and relaunch unattended bootstrap behavior for supported providers.

**Non-Goals:**

- Redesign the launch-policy registry schema unless implementation proves it is necessary.
- Change the supported unattended provider inputs or the selected Claude strategy itself.
- Add a new public CLI family for tmux attach beyond improving the current launch handoff behavior.
- Repair arbitrary user-owned provider files outside the strategy-declared owned-path surface.

## Decisions

### 1. Split launch-plan behavior by operation intent

`build_launch_plan()` currently treats resume/control and provider-start as the same kind of work. This change will introduce an explicit launch-plan intent boundary such as `provider_start` versus `resume_control`.

For `resume_control`, the runtime will load the persisted manifest, home selector, launch-policy provenance, and backend continuity metadata needed to control the live session, but it will not re-run strategy actions that mutate provider-owned files merely to inspect state, prompt a live TUI, or query gateway status.

For `provider_start` or relaunch paths that will actually start a provider process again, the runtime will continue to apply unattended bootstrap logic before process start.

Why this approach:

- It removes the self-race from the common read-only path instead of only papering over it with retries.
- It better matches the real semantics: `agents state` and `gateway status` are not provider bootstrap actions.

Alternatives considered:

- Keep reapplying all unattended actions on every resume and add retries around malformed JSON reads.
  Rejected because it leaves needless mutation on read-only flows and still allows partial-read races.
- Put a coarse global lock around every resumed control command.
  Rejected because it would serialize unrelated inspection operations and still conflates control with provider bootstrap.

### 2. Provider-state mutation remains allowed only on explicit provider-start paths and must be serialized plus atomic

When a start or relaunch path must create, patch, or repair strategy-owned files such as Claude `settings.json` or `.claude.json`, that mutation will run under a per-runtime-home lock. Writes will use a temp-file plus atomic replacement pattern instead of truncate-then-write.

This applies to both JSON and TOML helpers under the shared provider-state utility layer. If the implementation must recover from a blank or malformed strategy-owned file created by the previous unsafe behavior, that repair is allowed only inside this serialized pre-start mutation phase.

Why this approach:

- It prevents readers from seeing a zero-byte or half-written file.
- It gives relaunch and future provider-start flows a safe way to recover from prior damage without keeping unsafe mutation on ordinary control commands.

Alternatives considered:

- Only make writes atomic, but keep them on all resume/control paths.
  Rejected because atomic writes reduce corruption but do not justify unnecessary mutation during `state` or `gateway status`.
- Only skip writes on resume/control and leave provider-start writes non-atomic.
  Rejected because concurrent start or relaunch paths would still have the same class of race.

### 3. Launch handoff becomes interactivity-aware and libtmux-first

After a successful non-headless launch, the CLI will resolve the tmux session through the repo-owned libtmux integration layer. If the caller has a usable interactive terminal, the CLI may perform session handoff through libtmux-owned command dispatch. If the caller does not have a usable TTY, the CLI will skip attach entirely, keep the launch successful, and emit the tmux session coordinates needed for a later manual attach.

Why this approach:

- The launch command should not turn a successful runtime startup into an apparent failure merely because the caller is non-interactive.
- It aligns the last remaining launch-handoff tmux path with the libtmux-first rule already adopted elsewhere.

Alternatives considered:

- Keep the raw `tmux attach-session` subprocess and suppress its stderr.
  Rejected because it still violates the tmux integration boundary and hides the cause instead of fixing the contract.
- Treat non-interactive launch as implicit headless mode.
  Rejected because the runtime still intentionally created a tmux-backed interactive session; only the immediate operator handoff is unavailable.

### 4. Successful launch remains keyed to live session readiness, not to attach success

This change does not weaken launch correctness. The runtime must still establish the intended tmux-backed provider surface and reach the existing ready-or-live criteria before launch is reported as successful. The only change is that terminal handoff is no longer part of success when the caller has no terminal that can accept the handoff.

## Risks / Trade-offs

- [Resume/control now depends more heavily on persisted launch metadata instead of recomputing launch-policy mutations] -> Mitigation: preserve launch-policy provenance and home selector data in the manifest and keep provider-start validation on relaunch paths.
- [Per-home locking can serialize some start or relaunch operations] -> Mitigation: keep read-only control paths outside the mutation lock; only provider-start repair paths pay the serialization cost.
- [libtmux does not make terminal attach portable by itself] -> Mitigation: treat attach as a TTY-gated handoff operation, and use libtmux-owned command dispatch only when a real terminal is present.
- [Existing homes damaged by the previous race may still contain malformed owned files] -> Mitigation: allow serialized pre-start repair for strategy-owned files during next provider-start or relaunch.

## Migration Plan

No repository-wide migration is required.

Implementation rollout:

1. Introduce the resume-vs-start intent split for launch-plan composition and apply it to local resumed control commands.
2. Move provider-state writes onto serialized atomic helpers.
3. Switch launch handoff onto the libtmux-first path with explicit TTY detection.
4. Add regression tests for non-interactive launch, concurrent resumed control, and relaunch repair.

Rollback strategy:

- The change is code-only and can be reverted normally.
- Existing manifests and runtime homes remain structurally compatible because the persisted contract stays centered on manifest metadata and strategy-owned home files.

## Open Questions

- None blocking for the proposal. A minor follow-up choice is whether non-interactive launch should emit an explicit `attach_command` helper field in addition to the already printed tmux session name.
