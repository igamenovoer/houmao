# Proposal

## Why

Managed Hermes TUI can report that it is ready while the manager refuses its prompt through the terminal parser. Detached Hermes service and TUI tools also fail self verification, which blocks the mailbox workflows reported in [issue #104](https://github.com/igamenovoer/houmao/issues/104).

## What Changes

- Route direct manager prompts for Hermes TUI through native admission. Carry one owner claim from the final readiness check through the durable receipt and report the verified result for that request.
- Verify detached Hermes service and TUI callers against the current managed generation and the recorded native daemon. Publish a private locator when Houmao verifies a daemon for the managed home, including supported same-home adoption.
- Use the verified native owner for managed-self gateway liveness so authorized mail commands can use their existing proof when the viewer is absent.
- Reconcile manager-backed fixture prompt and stop against the runtime captured by the run. Report the manager exit code and path to its private diagnostics, and retain the launch identity when an initial prompt fails.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `hermes-agent-runtime` specifies the manager prompt result and the native authority shared with gateway admission.
- `houmao-managed-agent-self-identity` specifies how detached Hermes tool processes prove current managed self.
- `authenticated-gateway-access` specifies liveness for verified Hermes generations using their existing managed-self registrations.
- `houmao-mgr-agents-scope-cli` recognizes verified Hermes daemon authority in the self scope.
- `houmao-srv-ctrl-native-cli` specifies detached self mailbox discovery and refusal when current authority is unavailable.
- `docs-cli-reference` describes verified detached Hermes targeting alongside tmux-based self targeting.
- `test-agent-launch-fixtures` specifies current manager lifecycle reconciliation and private failure diagnostics.

## Impact

The change affects manager prompt dispatch, Hermes runtime evidence, self targeting, gateway proof, and the developer fixture CLI. It uses the existing product commands, prompt result fields, and gateway proof protocol. Qualification covers direct and delegated prompts, detached Hermes self commands, and fixture follow-up after an explicit relaunch.
