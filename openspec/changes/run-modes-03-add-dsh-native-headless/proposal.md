# Proposal

## Why

DSH ships a one-shot runner with structured events and exact continuation. Houmao currently creates and closes an ACP server per turn, which gives the `headless` selection different semantics from the underlying CLI.

## What Changes

- **BREAKING** Bind `(dsh, headless)` to `dsh_headless` using the shipped headless profile, JSON event stream, and exactly one native invocation per request.
- Retain the logical managed agent, native conversation selection, role and private home, canonical artifacts, dispatch evidence, interruption, and journal accounting across workers.
- Validate the new profile against actual DSH native configuration. Reject ACP-only input on this mode before mutation and direct users to the service lane where appropriate.
- Migrate the passive headless launch route and fixtures to the CLI runner. Distinguish historical per-turn ACP evidence from new native headless qualification.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `dsh-headless-control` changes worker execution, continuation, evidence, interruption, and current-home rules to the native one-shot profile.
- `brain-launch-runtime` replaces the headless-to-ACP mapping and updates per-turn lifecycle.
- `passive-server-headless-management` launches the one-shot adapter and preserves its native CLI artifacts.
- `test-agent-launch-fixtures` exercises the actual headless profile in raw and managed cases.

## Impact

Affects the DSH launch plan and policy, headless runtime adapter, `tool_params` backend validation, native event/usage collection, passive-server headless birth, and DSH qualification. The already maintained DSH Web path remains a separate fixture lane.

## Dependencies

Direct prerequisite for implementation and spec synchronization is `run-modes-02-unify-managed-agent-control`. Can proceed alongside 04 and 07. Release the change together with 01, 02, and 04 for the DSH cutover.
