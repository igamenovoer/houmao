## Why

Steps 1–6 established the passive server's runtime and client-facing capabilities, but Step 8 should not retire the old `houmao-server` until there is repeatable evidence that both authorities behave consistently enough in shared-registry workflows. We need a canonical Step 7 validation surface now so maintainers can run both servers side by side, compare outcomes, and preserve evidence for any parity gaps before the passive server becomes the default.

## What Changes

- Add a canonical dual-authority validation workflow that starts `houmao-server` and `houmao-passive-server` in parallel against one isolated shared registry and runtime root.
- Define stepwise and unattended validation surfaces that exercise the Step 7 checks from the migration plan: shared discovery, managed state/detail/history parity, gateway proxy behavior through the passive server, passive-server-launched headless visibility from the old server, and cross-authority stop propagation.
- Require preserved machine-readable evidence and comparison artifacts for each validation phase so mismatches between the two authorities are explicit, reviewable, and reproducible.
- Provide operator guidance for running the parallel validator on separate ports without mutating the repository checkout or relying on ad hoc shell state.
- Keep the Step 7 change scoped to validation and evidence capture; any parity gaps uncovered by the validator should be fixed in targeted follow-up changes unless a minimal co-landed fix is required to keep the canonical validator runnable.

## Capabilities

### New Capabilities
- `passive-server-parallel-validation`: A canonical side-by-side validation workflow for `houmao-server` and `houmao-passive-server`, including environment setup, launch/provision flows, cross-authority comparison checks, and preserved evidence for migration readiness.

### Modified Capabilities
<!-- No spec-level requirement changes to existing passive-server runtime capabilities are needed. This change adds the validation contract that proves the already-specified capabilities are ready for Step 8 retirement work. -->

## Impact

- **Code and assets**: New validation assets under `scripts/demo/` and related helper code for running two authorities, driving shared-registry scenarios, and comparing results.
- **Validation**: New live/demo coverage for discovery parity, managed-agent state parity, passive-server gateway forwarding, passive-server headless visibility across authorities, and cross-authority stop behavior.
- **Operators**: Maintainers gain one documented, repeatable Step 7 workflow for deciding whether the passive server is ready to replace the old server.
- **Follow-up flow**: Validation failures become concrete evidence for subsequent fix changes instead of informal notes or one-off manual experiments.
