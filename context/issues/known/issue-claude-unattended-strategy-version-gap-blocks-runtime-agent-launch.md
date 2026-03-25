# Issue: Claude Unattended Strategy Version Gap Blocks Runtime Agent Launch

## Priority
P1 - Claude-based managed launches can fail completely on healthy systems after a provider upgrade, even though the runtime and TUI backend code paths are otherwise correct.

## Status
Open as of 2026-03-25.

## Summary

Local managed Claude launch currently fails before provider startup when the selected recipe requests `launch_policy.operator_prompt_mode: unattended` and the installed Claude Code version is newer than the latest strategy covered by the launch-policy registry.

On this machine, installed Claude Code is `2.1.83`, but the only registered Claude unattended strategy is `claude-unattended-2.1.81` with version range `>=2.1.81, <2.1.82`. As a result:

- no-server interactive launch fails before tmux/provider TUI startup
- no-server headless Claude launch fails the same way
- the new local interactive backend is never reached for unattended Claude launch on this version

This is not primarily a `local_interactive` backend bug. The TUI change exposed an underlying launch-policy compatibility gap that already affects Claude runtime-managed launch more broadly.

## Reproduction

### Interactive no-server launch

```bash
AGENTSYS_AGENT_DEF_DIR=/data1/huangzhe/code/houmao/tests/fixtures/agents \
pixi run houmao-mgr agents launch \
  --agents gpu-kernel-coder \
  --provider claude_code \
  --session-name verify-local-interactive \
  --yolo
```

### Headless no-server launch

```bash
AGENTSYS_AGENT_DEF_DIR=/data1/huangzhe/code/houmao/tests/fixtures/agents \
pixi run houmao-mgr agents launch \
  --agents gpu-kernel-coder \
  --provider claude_code \
  --headless \
  --yolo
```

Observed failure for both:

```text
No compatible unattended launch strategy exists for tool='claude', backend='raw_launch', version='2.1.83'.
```

and

```text
No compatible unattended launch strategy exists for tool='claude', backend='claude_headless', version='2.1.83'.
```

## Evidence

### 1. The fixture recipe explicitly requests unattended launch

The Claude fixture used for local launch testing declares:

- `launch_policy.operator_prompt_mode: unattended`

Source:

- `tests/fixtures/agents/brains/brain-recipes/claude/gpu-kernel-coder-default.yaml`

### 2. `agents launch` now correctly preserves that policy into brain build

The no-server launch path forwards `target.recipe.operator_prompt_mode` into `BuildRequest(...)`:

- `src/houmao/srv_ctrl/commands/agents/core.py`

So the failure is not caused by policy being dropped anymore.

### 3. Launch-plan composition applies unattended policy before provider startup

`build_launch_plan()` reads the preserved manifest policy and calls `apply_launch_policy(...)` before runtime session startup:

- `src/houmao/agents/realm_controller/launch_plan.py`

For non-headless Claude launch, the local interactive backend is mapped to the `raw_launch` policy surface. For headless Claude launch, policy resolution runs against `claude_headless`.

### 4. Claude unattended registry only covers one narrow version window

The only Claude unattended strategy in the registry is:

- `strategy_id: claude-unattended-2.1.81`
- `backends: raw_launch, claude_headless, cao_rest, houmao_server_rest`
- `version_range: min_inclusive=2.1.81, max_exclusive=2.1.82`

Source:

- `src/houmao/agents/launch_policy/registry/claude.yaml`

So installed Claude `2.1.83` matches the tool family and supported backends, but falls outside the declared strategy range.

### 5. The runtime is intentionally fail-closed here

This behavior is consistent with the current OpenSpec runtime contract:

- `openspec/specs/brain-launch-runtime/spec.md`
- `openspec/specs/claude-cli-noninteractive-startup/spec.md`

Those specs require the runtime to:

- probe the real tool version
- select a compatible unattended strategy before provider startup
- fail before process start if no compatible strategy exists

So the immediate failure is expected under the current launch-policy contract.

## Root Cause

The direct cause is stale provider-version compatibility data in the Claude unattended launch-policy registry.

The deeper issue is that the system now depends on strategy coverage as an operational capability boundary, but several surrounding contracts and test surfaces still make the overall feature look more unconditional than it really is.

In other words:

1. The runtime behavior is internally consistent.
2. The installed provider version moved ahead of the registry.
3. The higher-level `agents launch` contract does not make that dependency visible enough to operators and tests.

## Why This Is More Than A Minor Data Bump

This is not just a single bad version constant.

### A. The user-facing launch contract hides a capability dependency

`houmao-mgr agents launch` says interactive launch starts the provider TUI in tmux, but in practice that is only true if the selected recipe's unattended launch policy is satisfiable for the installed provider version.

That means a basic "launch Claude TUI" smoke test is currently coupled to "the unattended Claude strategy registry is up to date for the local installation."

That coupling is real system behavior, not just a one-off bad fixture.

### B. The transient strategy override contract is broken on runtime-managed launch

OpenSpec says runtime launch should support:

```text
HOUMAO_LAUNCH_POLICY_OVERRIDE_STRATEGY=<strategy-id>
```

for controlled unattended-launch experiments.

But `build_launch_plan()` passes launch-policy `env` from the resolved runtime env payload rather than the parent process environment:

- `src/houmao/agents/realm_controller/launch_plan.py`

That means process-level override experiments do not reach `apply_launch_policy()` on runtime-managed launch unless the override env var is also present in the selected runtime env set.

So there is a real contract bug here, not just stale Claude metadata.

### C. The tests are too structural for a version-gated capability

Current tests verify:

- operator prompt mode is forwarded into brain build
- non-headless launch selects `local_interactive`
- local managed-agent state/history routes treat that backend as TUI

Those are good structural tests, but they do not verify that the default unattended Claude fixture still launches against the currently installed Claude version.

That leaves the repository exposed to provider-version drift without an operational guardrail.

## Design / Contract Assessment

### Not a fundamental architecture failure

The shared launch-policy engine and fail-closed unattended semantics are coherent.

Reusing the same policy system across:

- raw launch helpers
- runtime-managed headless sessions
- runtime-managed local interactive sessions

is the right architectural direction.

### But there is a system integration problem

This issue sits at the boundary between:

- provider-version-specific launch policy maintenance
- recipe defaults
- user-facing launch expectations
- runtime override/debug mechanisms

So the problem should be treated as a medium-sized system integration flaw:

- the immediate blocker is a missing Claude `2.1.83` unattended strategy
- the broader problem is that launch-policy capability drift is not surfaced or tested robustly enough

## Current Workarounds

### Workaround A: Use an interactive recipe/policy instead of unattended

If the goal is only to manually inspect a TUI and not to test unattended startup, use a recipe or launch path that does not request `operator_prompt_mode: unattended`.

This avoids launch-policy strategy resolution entirely.

### Workaround B: Patch the Claude unattended registry for the installed version

Adding or broadening a Claude strategy that is valid for `2.1.83` should unblock both interactive and headless runtime-managed Claude launch.

### Workaround C: Launch through a manual/debug path that bypasses runtime-managed unattended policy

Useful for local diagnosis only. This does not fix the broken managed-launch contract.

## Desired Direction

### 1. Repair the immediate capability gap

Add a Claude unattended strategy that covers installed Claude Code `2.1.83`, or widen the existing version range only after validating the strategy assumptions for that version.

### 2. Fix the runtime override contract

Ensure `HOUMAO_LAUNCH_POLICY_OVERRIDE_STRATEGY` is visible to runtime-managed launch-policy resolution exactly as the spec promises.

### 3. Clarify the user-facing contract

`houmao-mgr agents launch` should make it clearer when launch success depends on unattended policy compatibility for the installed provider version.

At minimum, startup failures should clearly distinguish:

- launch-mode/backend selection succeeded
- provider startup was blocked by missing unattended strategy support for the detected version

### 4. Add operational coverage

The repo needs at least one coverage path that fails when:

- the default unattended Claude fixture drifts out of compatibility with the installed Claude version

This could be a live probe, a version-compatibility smoke test, or a maintained fixture check that explicitly validates strategy coverage assumptions.

## Acceptance Criteria

1. A Claude recipe that requests unattended launch either:
   - starts successfully on supported installed versions, or
   - fails with a precise version/capability error before provider startup.
2. The runtime-managed launch path honors `HOUMAO_LAUNCH_POLICY_OVERRIDE_STRATEGY` as documented.
3. The default no-server Claude launch workflow does not silently depend on hidden strategy drift without diagnostics.
4. Coverage exists for provider-version drift on the maintained Claude unattended launch path.

## Connections

- OpenSpec runtime launch policy contract:
  - `openspec/specs/brain-launch-runtime/spec.md`
- OpenSpec Claude unattended startup contract:
  - `openspec/specs/claude-cli-noninteractive-startup/spec.md`
- Related launch-mode change that exposed the gap:
  - `openspec/changes/archive/2026-03-25-fix-local-interactive-agent-launch/`
