# Reporting Contract

Use this reference when the authored plan or run charter needs to define what the root owner should report for status, completion, or stop.

## Status Fields

- run phase
- active components by `component_id` and `component_type`
- active pairwise components and their driver-worker posture
- active relay components and their origin/ingress/egress posture
- latest receipt or final-result posture per component
- completed component results
- blockers or late conditions
- next planned actions
- completion-condition posture
- stop-condition posture when relevant

## Completion Fields

- final synthesized result
- why the completion condition is satisfied
- component results used to satisfy completion
- pairwise drivers that integrated local-close results when relevant
- relay egresses that returned final results to their origins when relevant
- relevant plan or run references when needed

## Stop Summary Fields

- stop mode used
- which components completed before stop
- which active pairwise components were interrupted or drained
- which active relay components were interrupted or drained
- preserved partial results
- remaining unfinished work or known blockers

## Guardrails

- Keep status current and operational rather than historical by default.
- Keep completion and stop summaries tied to the authored completion and stop conditions.
- Do not flatten component-specific state into an ambiguous single "worker graph" summary when the plan has typed components.
