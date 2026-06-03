## Context

`houmao-mgr` already suppresses Python tracebacks for normal operator use through the top-level Click entrypoint. That is the right default, but the current fallback converts any uncaught exception to `str(exc) or exc.__class__.__name__`, so an empty `AssertionError` becomes the entire user-facing message.

The observed `houmao-mgr agents single --agent-name alice gateway status` failure comes from a stale active managed-agent record. Target resolution correctly classifies the target as `local_stale` with a registry record and no live controller. `stop` and `relaunch` understand that target mode, but gateway and several other command helpers assume that every non-server target has `target.controller` and use `assert target.controller is not None`. That assertion is a runtime guard for an operator-visible state, not an internal invariant.

## Goals / Non-Goals

**Goals:**

- Make maintained `houmao-mgr` command failures explain the root cause, affected target, evidence, and next action when the failure is caused by user, environment, project, registry, or runtime state.
- Prevent bare implementation-level messages such as `AssertionError`, `KeyError`, empty `ValueError`, or assertion text meant for tests from being the primary CLI error.
- Add shared handling for stale or degraded local managed-agent targets across gateway, mail, state, prompt, interrupt, workspace, and scoped command families that require a live local controller.
- Preserve concise normal CLI output and keep tracebacks hidden unless a future explicit debug surface is introduced.

**Non-Goals:**

- Do not add a new CLI debug flag in this change.
- Do not change registry storage formats, lifecycle semantics, or pair HTTP API contracts.
- Do not make every unexpected programming bug recoverable. Unknown bugs should be identifiable and reportable, not disguised as normal user mistakes.

## Decisions

### Use a shared local-target guard for operations that require a live controller

Add a shared helper in the maintained managed-agent command layer that validates the resolved `ManagedAgentTarget` before local controller use. The helper should accept the operation name and target, return the controller when available, and raise `click.ClickException` when the target is `local_stale`, `local_degraded`, or otherwise lacks the authority required for that operation.

Alternative considered: fix only `gateway_status`. That would address the reported command but leave the same assertion shape in gateway TUI, reminders, mail notifier, mail commands, prompt, interrupt, state/detail, and workspace helpers.

### Format stale/degraded diagnostics from registry evidence

For stale or degraded local targets, the diagnostic should use data already present on the record: friendly name, agent id, lifecycle state, tmux session, manifest path, session root, and detected health state when available. The message should name the requested operation and include recovery commands such as `houmao-mgr agents single --agent-id <id> stop`, `houmao-mgr agents single --agent-id <id> relaunch`, `houmao-mgr agents global list`, or `houmao-mgr admin cleanup registry --dry-run`, depending on the state.

Alternative considered: always auto-recover stale records when any command encounters them. That is too surprising for inspection commands. `stop` and `relaunch` can continue owning lifecycle mutation; read/control commands should explain why the live authority is unavailable.

### Keep domain translation close to the failing command family

Known state failures should be translated before they reach the root fallback. The top-level handler should remain a last-resort renderer for unexpected bugs. This keeps messages specific: gateway commands can mention gateway availability, mail commands can mention mailbox/gateway prerequisites, and state commands can mention managed-agent authority.

Alternative considered: centralize every exception at `main.py`. That would reduce call-site changes, but the root handler lacks operation-specific context and cannot reliably infer user action.

### Make the uncaught fallback safe but visibly internal

Change the root fallback so an uncaught exception with no useful message renders as an unexpected internal error, not as a bare class name. Include the exception class as diagnostic evidence and include the non-empty exception message when present. Continue suppressing tracebacks in normal output.

Alternative considered: re-raise uncaught exceptions and show tracebacks. That helps developers but makes ordinary operator output noisy and inconsistent with existing tests.

## Risks / Trade-offs

- [Risk] Shared guard messages can become too generic. → Mitigation: pass operation names and format stale/degraded managed-agent evidence from the target record.
- [Risk] Replacing asserts may hide programming mistakes. → Mitigation: only convert target shapes that are valid domain states; truly impossible shapes still reach the explicit internal-error fallback.
- [Risk] The scan may uncover many `str(exc)` conversions. → Mitigation: prioritize maintained public CLI surfaces and add follow-up tasks only for low-risk wording improvements outside this change.
- [Risk] Tests may overfit exact prose. → Mitigation: assert stable facts such as target name/id, stale/degraded state, recovery command, and absence of bare implementation class messages.
