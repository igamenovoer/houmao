## Context

The current CAO launcher reports startup success once `GET /health` becomes healthy, but the process is still launched in a way that is coupled to the lifetime of the invoking command. In the interactive demo this creates a split-brain failure mode: the tmux-backed agent session survives, while the fixed-loopback CAO REST API disappears before later `inspect`, `send-turn`, or `send-keys` calls.

This change spans the generic launcher, the interactive demo startup path, and the launcher tutorial pack. It also changes operator-visible behavior: interactive demo startup should no longer ask whether to reuse an existing verified loopback CAO service when recreating an agent. Instead, the demo should deterministically stop the verified fixed-port service and launch a fresh standalone CAO instance for the new run.

## Goals / Non-Goals

**Goals:**
- Make launcher `start` mean "bootstrap a standalone detached CAO service and verify it became healthy".
- Ensure launcher-managed CAO remains reachable after the `start` command exits.
- Give the launcher enough artifact metadata to verify and stop the detached service later without relying on an in-memory `Popen` handle.
- Make interactive demo agent recreation force-replace the verified fixed-loopback CAO service instead of routing through a confirmation prompt.
- Update demo pack verification so it proves the standalone-service contract rather than only checking immediate startup success.

**Non-Goals:**
- Changing upstream CAO host/port behavior beyond the current fixed loopback support.
- Introducing a general-purpose multi-service supervisor for CAO processes.
- Preserving the current interactive demo replacement prompt behavior.
- Solving unrelated tmux/session-level failures inside CAO providers.

## Decisions

### 1. Launcher `start` will create a detached standalone service, not a parent-lifetime-bound child

The launcher bootstrap may still invoke `cao-server` from Python, but the launched service must be detached from the calling command's process/session lifetime. The success contract becomes: once `start` returns healthy, later launcher `status` calls against the same base URL must be able to reach the same CAO service unless it is explicitly stopped or crashes independently.

Why this over the current model:
- The current model only proves "healthy once" and not "healthy after launcher exit".
- The interactive demo depends on follow-up commands being able to talk to the same CAO REST API.

Alternatives considered:
- Keep the current subprocess model and add more retries in `inspect`/`send-turn`: rejected because it treats symptom rather than lifecycle contract.
- Introduce an external system supervisor requirement: rejected because it adds environment complexity to a repo-local demo workflow.

### 2. Launcher artifacts will describe service ownership, not just PID/log paths

The launcher already writes pid/log artifacts. This change extends that contract with structured ownership metadata under the same `<runtime_root>/cao-server/<host>-<port>/` directory, for example:

```text
runtime_root/cao-server/<host>-<port>/
├── cao-server.pid
├── cao-server.log
├── launcher_result.json
└── ownership.json
```

`ownership.json` should capture enough information to answer:
- which base URL this service owns
- which home directory/runtime root it was started with
- when it was started
- optionally a config fingerprint for diagnostics

Why this over pidfile-only state:
- Pidfiles are necessary but too weak for diagnosing stale or mismatched service ownership.
- The interactive demo needs a clearer distinction between "verified CAO we own" and "some other loopback occupant".

Alternatives considered:
- Keep only pid/log/launcher_result: rejected because it leaves verification and debugging too opaque.
- Store ownership only in memory during `start`: rejected because later `status` and `stop` calls are separate processes.

### 3. Interactive demo startup will always replace the verified fixed-loopback CAO service during agent recreation

For `http://127.0.0.1:9889`, interactive demo startup should follow a deterministic sequence:

```text
status -> verify occupant -> stop verified CAO -> wait for port clear -> start fresh CAO -> verify health -> start agent session
```

There is no operator confirmation branch for this replacement anymore. `-y` remains accepted by the wrapper surface for consistency, but it no longer controls CAO replacement in this flow.

Why this over the current prompt-based behavior:
- The demo is already opinionated about using one fixed loopback target and one active run marker.
- Agent recreation should not leave correctness up to an interactive prompt branch.
- The user requirement is explicit: force close on agent recreation.

Alternatives considered:
- Preserve prompt-by-default and only bypass with `-y`: rejected because it keeps recreation nondeterministic.
- Teach the launcher a new `--replace` mode and keep demo logic thin: plausible, but not required for the first fix if demo can already sequence `status`/`stop`/`start`.

### 4. Demo-pack verification will explicitly prove post-start service survivability

The CAO launcher demo pack should validate more than immediate start success. Its report contract should include a `status_after_start` check performed after the `start` command has completed, so the maintained fixture proves the service remained reachable across command boundaries.

Why this matters:
- The current failure mode passed initial startup but broke later commands.
- The tutorial-pack should guard the launcher contract that other flows depend on.

Alternatives considered:
- Leave the demo pack unchanged and rely on interactive demo tests alone: rejected because the launcher pack is the canonical place to verify launcher lifecycle behavior in isolation.

## Risks / Trade-offs

- [Detached service startup behaves differently across platforms] → Keep the supported scope limited to the current loopback CAO environments and verify with launcher integration tests on this repo's supported platform set.
- [Ownership metadata drifts from actual process state] → Treat ownership metadata as diagnostics and verification support, not as a replacement for live health checks and pid verification.
- [Automatic replacement surprises operators who expected the old prompt] → Document the breaking change in the interactive demo README and spec delta; repo-local callers should be updated rather than shimmed.
- [Detached CAO still crashes independently after successful start] → Require post-start status verification in the launcher demo pack and interactive demo tests so regressions are caught quickly.

## Migration Plan

1. Update launcher semantics and artifact contract.
2. Update interactive demo startup to remove the CAO replacement prompt path and always recycle the verified fixed-port service before agent recreation.
3. Refresh launcher demo pack expectations to include standalone-service survivability and new ownership artifact/report fields.
4. Update repo docs and in-repo callers to the new behavior; no compatibility shim is required for the old interactive prompt path.

Rollback strategy:
- Revert the launcher detached-service changes and restore the previous prompt-based demo startup path.
- Restore the previous expected reports if the new lifecycle contract proves unsound.

## Open Questions

- Whether to expose a first-class launcher CLI flag such as `start --replace` now, or keep replacement sequencing in the interactive demo for the first iteration.
- Whether the interactive demo `stop` flow should also stop the standalone fixed-loopback CAO service automatically, or keep CAO lifecycle ownership scoped to startup/recreation only.
