## Why

The `gateway-mail-wakeup-demo-pack` still covers a valid gateway-specific behavior, but its defaults have drifted from the repository's newer fixture guidance. It still provisions a repository git worktree and the heavyweight `gpu-kernel-coder` Codex blueprint even though the repo now prefers copied dummy projects and the lightweight `mailbox-demo` role family for narrow mailbox and runtime-contract demos.

That drift makes the pack more expensive and less deterministic than it needs to be, and it leaves the repository with only unit-level coverage for the pack's helper logic rather than a stronger regression story for the live wake-up path.

## What Changes

- Refresh the gateway wake-up demo pack so its default agent fixture shape matches the current repository guidance for narrow mailbox and runtime-contract demos.
- Replace the demo's repository-worktree provisioning with copied dummy-project provisioning under the demo-owned output directory, initialized as a fresh standalone git-backed workdir.
- Switch the tracked default agent blueprint from the heavyweight `gpu-kernel-coder` family to the lightweight `mailbox-demo` family.
- Update the tutorial README, tracked parameters, and expected-report contract so they describe the new fixture shape clearly and stop teaching repository-worktree assumptions as the default path.
- Add stronger automated coverage for the pack's start/auto/reporting workflow so fixture drift and wake-up-path regressions are easier to catch.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `gateway-mail-wakeup-demo-pack`: Change the demo-pack requirements so the default wake-up tutorial uses the repository's dummy-project and lightweight mailbox-demo fixtures, and so its verification and documentation reflect that narrower fixture model plus stronger regression coverage expectations.

## Impact

- Affected code: `scripts/demo/gateway-mail-wakeup-demo-pack/*`
- Affected tests: `tests/unit/demo/test_gateway_mail_wakeup_demo_pack.py` and likely a new or expanded integration/demo regression lane
- Affected docs/specs: `openspec/specs/gateway-mail-wakeup-demo-pack/spec.md` plus documentation that points readers at this pack as the runnable gateway wake-up walkthrough
- No public API change is intended; the work is a fixture/defaults refresh and regression-hardening change for an existing demo pack
