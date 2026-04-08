## Context

Managed gateway execution mode is currently selected inconsistently across the stack. Runtime-owned `houmao-mgr agents gateway attach` defaults to detached background execution unless the operator passes `--foreground`, while pair-managed `houmao_server_rest` sessions already use same-session auxiliary-window execution by default. Launch-time gateway auto-attach in `project easy instance launch` does not expose any execution-mode control at all and currently falls through to backend defaults.

The code paths reflect that split: local attach helpers pass an explicit foreground override only for `--foreground`, pair-managed attach calls `POST /houmao/agents/{agent_ref}/gateway/attach` without a request body, and easy auto-attach calls `controller.attach_gateway()` without an execution-mode override. The tmux-side machinery for same-session auxiliary windows already exists and already enforces the important surface contract that window `0` remains the managed-agent surface and the gateway window uses index `>=1`.

Foreground-by-default therefore requires a coordinated contract change across CLI entrypoints, runtime attach plumbing, pair client/server transport, and human-oriented status rendering.

## Goals / Non-Goals

**Goals:**

- Make foreground same-session auxiliary-window execution the default managed-gateway posture for tmux-backed managed sessions.
- Add explicit background opt-out controls for manual attach and easy launch auto-attach.
- Carry one execution-mode choice end-to-end across runtime-owned and pair-managed attach flows instead of relying on backend-default fallthrough.
- Keep the agent-surface contract intact: tmux window `0` remains the agent surface and the live gateway window must stay non-zero.
- Ensure status and attach output remain useful when foreground execution becomes the common case.

**Non-Goals:**

- Introduce persisted launch-profile fields for gateway execution mode in this change.
- Change gateway behavior for non-tmux-backed or non-managed attach flows.
- Preserve the old `--foreground` CLI flag as a compatibility alias.
- Redesign gateway lifecycle semantics beyond the execution-mode default and explicit background override.

## Decisions

### Resolve managed attach mode explicitly instead of flipping raw backend defaults

Managed attach flows will resolve an explicit effective execution mode at the command or managed-launch boundary and pass it downstream, rather than globally changing low-level backend defaults.

Why this approach:

- It limits the behavior change to user-facing managed attach flows instead of silently changing every internal caller that currently omits an override.
- It keeps detached background execution available as an intentional explicit mode rather than as implicit backend fallback.
- It lets the easy-launch and attach-later surfaces share one clear policy without conflating that policy with unrelated lower-level runtime helpers.

Alternative considered:

- Change the backend default resolver so any omitted execution mode becomes foreground for tmux-backed backends.
- Rejected because it would broaden the blast radius beyond the managed CLI contracts being changed here and would make it harder to reason about internal callers that intentionally rely on the existing defaulting behavior.

### Use `--background` as the only explicit manual attach override

`houmao-mgr agents gateway attach` will default to foreground same-session auxiliary-window execution for tmux-backed managed sessions. The command will accept `--background` as the explicit opt-out for detached execution and will no longer require or document `--foreground`.

Why this approach:

- It matches the desired operator contract directly: foreground is normal, background is exceptional.
- It keeps the CLI surface small and makes the default obvious from the help text.
- It avoids a confusing state where both `--foreground` and the absence of flags mean the same thing.

Alternative considered:

- Keep both `--foreground` and `--background` as mutually exclusive flags.
- Rejected because that preserves redundant syntax for the new default and dilutes the signal that foreground is now the standard managed attach posture.

### Give easy auto-attach a matching per-launch background override

`houmao-mgr project easy instance launch` will keep auto-attach enabled by default for gateway-capable launches and will resolve that auto-attach to foreground same-session auxiliary-window execution unless the operator explicitly requests background mode through a one-shot launch flag.

Why this approach:

- It aligns launch-time auto-attach with attach-later behavior so specialists do not produce two different gateway topologies depending on when the gateway was created.
- It satisfies the user-visible configurability requirement without introducing new persisted launch-profile schema in the same change.
- It keeps the easy lane opinionated while still allowing detached execution for scripts or low-visibility sessions.

Alternative considered:

- Add a persisted launch-profile execution-mode field now.
- Rejected because it broadens the change into launch-profile schema evolution before the default/override behavior has been proven on the core CLI surfaces.

### Extend pair-managed attach transport to carry execution mode explicitly

Pair-managed attach must gain an explicit execution-mode input rather than silently ignoring `--background`. The pair client, server route, and service method should accept an optional attach request payload that carries the desired managed execution mode, defaulting to foreground when omitted.

Why this approach:

- It makes runtime-owned and pair-managed attach semantics match at the user-facing CLI level.
- It avoids a misleading `--background` flag that works only for some targets or is silently ignored for pair-managed sessions.
- It keeps server-managed attach behavior inspectable and testable instead of encoding policy only in the local CLI wrapper.

Alternative considered:

- Treat `--background` as unsupported for pair-managed sessions.
- Rejected because it creates an inconsistent contract on the same command surface and leaves pair-managed gateway attach as a special case without strong product value.

### Promote foreground metadata into normal human-oriented status output

When foreground execution is active, `agents gateway attach` and `agents gateway status` should show `execution_mode` and the authoritative gateway tmux window index in plain and fancy renderers, not only in JSON.

Why this approach:

- Foreground becomes the default operator path, so the gateway window identifier becomes routine operational output rather than edge metadata.
- The existing spec already expects those fields, and the curated renderer currently omits them.
- It makes the new topology discoverable without forcing operators or system skills to switch to JSON mode.

Alternative considered:

- Leave the human-oriented renderers unchanged and rely on JSON for execution metadata.
- Rejected because it weakens the usability of the new default and hides the exact tmux surface operators are expected to inspect.

## Risks / Trade-offs

- [Risk] A visible auxiliary tmux window by default may surprise operators who were relying on fully detached gateway behavior. → Mitigation: keep `--background` and the easy-launch background override explicit and documented in CLI help and lifecycle docs.
- [Risk] Pair client/server changes add one more cross-version coordination point for managed attach. → Mitigation: make the request field optional with a foreground default so newer and older components fail only when the new override is actually required.
- [Risk] Foreground-by-default increases the importance of correct tmux window bookkeeping and status rendering. → Mitigation: add integration coverage for non-zero gateway window allocation, renderer coverage for `execution_mode` plus `gateway_tmux_window_index`, and regression tests for both attach-later and easy auto-attach.
- [Trade-off] This change intentionally breaks the old `--foreground` opt-in workflow. → Accept because the repository is in unstable development and the new default/flag shape is materially simpler.

## Migration Plan

There is no stored-data migration in this change.

Implementation rollout:

1. Update the managed CLI surfaces to resolve foreground as the default and accept explicit background overrides.
2. Thread the resolved execution mode through runtime-owned attach, easy launch auto-attach, and pair-managed attach transport.
3. Update gateway status rendering and CLI/docs/help text to reflect the new default.
4. Add targeted unit and tmux-backed integration coverage for default foreground attach, explicit background attach, and easy-launch auto-attach.

Rollback is a code revert of the CLI default/flag change plus the managed attach transport updates.

## Open Questions

- No product-level questions remain for this proposal. The main implementation detail to validate is the exact request model added to the pair-managed attach route so local and server-managed callers share one execution-mode vocabulary.
