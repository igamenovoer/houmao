## Context

`houmao-server-interactive-full-pipeline-demo` is meant to be a self-contained regression target for the supported `houmao-server + houmao-mgr` pair. Today the pack starts the demo-owned server with run-scoped filesystem roots and installs the tracked profile through a subprocess that uses the same scoped environment, but detached TUI launch still goes through an in-process private helper.

That private launch path now conflicts with two current pair behaviors:

- top-level `houmao-mgr launch --headless` is the Houmao-native headless launch path, not the detached TUI compatibility path
- delegated launch artifact materialization resolves runtime and registry roots from the caller environment when the demo does not pass its run-scoped env through a subprocess

The result is that the demo can create a live pair session but then fail to find its delegated manifest under the run root, because the manifest was written to the ambient Houmao runtime root instead. The pack also still documents and uses raw CAO session deletion for stop, even though the managed-agent API now defines `POST /houmao/agents/{agent_ref}/stop` as the public shared stop surface.

## Goals / Non-Goals

**Goals:**

- Make demo startup work against the current `houmao-server + houmao-mgr` pair semantics.
- Keep delegated runtime artifacts owned by the demo run root rather than ambient `~/.houmao/*` roots.
- Use public pair command and HTTP surfaces instead of private Python helpers for detached launch and normal stop.
- Refresh docs and tests so future pair-surface drift is caught quickly.

**Non-Goals:**

- Redesign prompt, interrupt, inspect, or verify behavior beyond the launch and stop fixes needed for current pair compatibility.
- Expand the demo beyond its current Claude and Codex provider coverage.
- Repair similar launch-surface drift in other demo packs as part of this change.

## Decisions

### 1. Use the explicit detached compatibility launch surface for TUI startup

The demo will stop importing the private `houmao-mgr` launch helper and will launch the interactive TUI session through a subprocess that invokes the public detached compatibility surface:

- `houmao-mgr cao launch --headless --yolo --agents gpu-kernel-coder --provider <provider> --port <port>`

That subprocess will run with `cwd=<demo workdir>`.

Rationale:

- `houmao-mgr cao launch --headless` is the public detached TUI compatibility path.
- top-level `houmao-mgr launch --headless` now means native headless launch and no longer matches the demo's TUI expectations.
- using the public CLI surface avoids coupling the demo to private internal helper signatures.

Alternatives considered:

- Keep calling the private `_launch_session_backed_pair_command` helper: rejected because it bypasses the public pair surface and makes the demo fragile when internal launch plumbing changes.
- Switch to top-level `houmao-mgr launch --headless`: rejected because that route is the Houmao-native headless contract, not a detached TUI launch.

### 2. Scope both install and detached launch to the demo-owned environment

The demo will treat install and detached launch as part of the same run-scoped ownership boundary. Both subprocesses will receive the demo-built environment, including:

- demo-owned `HOME`
- `AGENTSYS_GLOBAL_RUNTIME_DIR`
- `AGENTSYS_GLOBAL_REGISTRY_DIR`
- `AGENTSYS_LOCAL_JOBS_DIR`

Startup will continue to look for delegated manifests and related artifacts under the demo run root only.

Rationale:

- delegated launch artifact materialization resolves runtime and registry roots from environment when no explicit runtime root is passed
- the pack already promises that each run provisions its own isolated roots
- searching ambient roots would hide ownership bugs and make the demo less deterministic

Alternatives considered:

- Keep launch in the ambient process and add fallback discovery in both demo-owned and ambient roots: rejected because it would preserve broken ownership and make artifacts depend on the operator shell.
- Add a one-off explicit runtime-root parameter to private launch internals: rejected because the public detached CLI path already exists and better represents the supported boundary.

### 3. Use the managed-agent stop route for normal teardown

The demo's normal stop flow will call:

- `POST /houmao/agents/{agent_ref}/stop`

The demo will still tolerate stale-session outcomes and mark local state inactive when the remote managed agent is already gone. Partial-start rollback may keep using best-effort raw session deletion because that cleanup can happen before managed-agent registration is complete.

Rationale:

- the managed-agent API is the public transport-neutral stop surface for both TUI-backed and headless agents
- using `/houmao/agents/{agent_ref}/stop` keeps the demo aligned with the supported operator contract
- startup rollback has a different failure mode than normal stop and may need a lower-level cleanup fallback before a managed-agent identity exists

Alternatives considered:

- Keep normal stop on `DELETE /cao/sessions/{session_name}`: rejected because it teaches the older compatibility route as the primary control surface and bypasses the shared managed-agent lifecycle seam.

### 4. Lock the regression tests to pair-surface selection and ownership

The unit tests will stop mocking the private launch helper and instead verify:

- detached startup uses the explicit `houmao-mgr cao launch --headless` command shape
- install and launch subprocesses receive the demo-owned environment
- stop targets the managed-agent stop client path for normal teardown

Rationale:

- the existing mocked tests allow internal/private coupling to drift without catching real contract changes
- the demo needs regression coverage on command selection and artifact ownership, not just on local helper wiring

## Risks / Trade-offs

- [CLI output wording drifts from the current wrapper assumptions] → Mitigation: assert stable effects in tests and runtime polling, not exact human-readable stdout.
- [Managed-agent stop can fail differently from raw CAO delete in partially registered states] → Mitigation: keep startup rollback separate from normal stop and preserve stale-state tolerance.
- [Ambient tool-specific env vars may still influence provider behavior in edge cases] → Mitigation: keep the core fix focused on AGENTSYS ownership roots now and extend env sanitization only if a concrete provider leak is reproduced.

## Migration Plan

1. Update the demo command implementation to launch through the public detached compatibility CLI with the demo-owned environment.
2. Switch normal stop to the managed-agent stop route while keeping best-effort partial-start cleanup behavior.
3. Refresh README and shell-wrapper wording so the operator workflow matches the new implementation.
4. Update unit tests to verify the public command surface and demo-owned artifact roots.

No production migration is required. Existing demo run roots remain disposable, and stale local state should continue to be treated as cleanup-safe.

## Open Questions

None for this change.
