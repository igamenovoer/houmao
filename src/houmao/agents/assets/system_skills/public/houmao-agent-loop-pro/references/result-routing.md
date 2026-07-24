# Result Routing

## Purpose

Use this page when generating or validating reply, result, and completion routing.

## Tree Loop

- Normal results return to the immediate upstream participant.
- A downstream participant does not bypass the immediate upstream for normal participant results.
- Terminal or operator reports may use explicit exceptions recorded in process and communication contracts.
- A parent aggregates child results only after local-close replies reach that parent.

## Generic Loop

- Result routing is task-specific and must be explicit.
- A route may reply to sender, forward to a downstream participant, report to an acceptance authority, or continue around a cycle when generated contracts define that behavior.
- Cycles need termination and repeat-visit posture.
- Message families should name reply or forward expectations when a reply or forward is expected.

## Validation

Check that generated contracts identify:
- expected result target;
- reply family or forward family when structured;
- handoff or exchange id fields;
- terminal result or completion authority when applicable;
- explicit exceptions to tree-loop local-close return.
