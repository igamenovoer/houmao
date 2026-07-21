# Observable Behavior Evidence Contract

## Workflow

1. **Inventory available sources** before execution and record expected visibility in the run manifest.
2. **Collect raw sources** during the declared observation window without adding oracle hints.
3. **Assign an authority tier and digest** to every collected item.
4. **Map each verdict claim to concrete evidence.** Use `unobservable` or `incomplete` when the required claim lacks authority.
5. **Keep raw evidence immutable** and put excerpts or interpretations in derived adjudication files.

If two observable sources disagree, use the native planning tool to compare their authority, timestamps, scope, and collection failure modes; preserve both and state the unresolved limitation.

## Authority Tiers

| Tier | Evidence | Supports |
| ---: | --- | --- |
| 1 | Provider-native skill invocation, tool-call, or skill-load event naming the selected root | Activation and explicit root selection |
| 2 | Observable skill file access, exact command trace, manager/gateway event, runtime transition, or bounded filesystem delta | Routing, actor gates, effects, and some root-selection claims when the host contract makes the mapping explicit |
| 3 | Raw terminal transcript, final response, visible clarification, or provider status surface | Outcome semantics, visible gates, and supporting behavior evidence |
| 4 | Evaluator notes and derived summaries | Interpretation only; never independent proof |

TUI tracker state is not an authority for system-skill activation or semantic routing. It may establish only capture timing or session posture when the case explicitly permits it as supporting infrastructure evidence.

## Activation Visibility

Assign activation `pass` or `fail` only when a source reliably identifies the selected root or reliably proves a forbidden root was selected. When behavior is visible but root selection is not, use `unobservable`. When expected activation instrumentation failed unexpectedly, use `incomplete`.

Non-activation cases require enough native or access evidence to establish that forbidden roots did not load. If a host exposes no such negative evidence, outcome behavior may pass while activation remains unobservable.

## Prohibited Evidence

- Hidden chain-of-thought, private scratchpads, or requests for the agent to reveal them.
- A post-hoc agent assertion about which skill it remembers using when no native event supports it.
- Exact prose similarity used as a substitute for semantic behavior.
- Tracker output used as the oracle for skill activation.
- Credential values or secret-bearing environment dumps.

## Guardrails

- DO NOT upgrade a Tier 3 resemblance into Tier 1 activation proof.
- DO NOT erase contradictory or failed instrumentation records.
- DO NOT quote private reasoning even when a provider exposes internal debug material accidentally.
