## Why

Houmao's advanced-usage guidance now covers a forward-relay loop where work can pass across multiple agents before a distant loop egress returns the final result to the origin. That model is useful, but it is more complex than many real workflows need. A second, simpler loop model is needed for cases where every delegation edge closes locally: the driver sends work to one worker, and that same worker returns the final result back to the same driver before any upstream reporting continues.

## What Changes

- Add a supported advanced-usage pattern for pairwise driver-worker edge loops where each loop round is closed between exactly two agents.
- Define the pairwise roles and local-close message flow: driver request, worker receipt, worker final result, and driver result acknowledgement.
- Specify that the simplified pattern is a sibling to the existing relay-loop pattern, not a replacement for it, and explain when to choose one versus the other.
- Specify that a worker may recursively become the driver of child edge-loops, but must close those child loops locally before reporting its own final result upstream.
- Use one edge-local workflow identifier such as `edge_loop_id` plus optional `parent_edge_loop_id` rather than the more distant relay-e2e identity model.
- Specify that mutable edge-loop bookkeeping lives under `HOUMAO_JOB_DIR` and not under `HOUMAO_MEMORY_DIR`.
- Define the recommended supervision model for multiple concurrent edge-loops: one local ledger, one supervisor reminder, and optional self-mail checkpoint as a backlog pointer.
- Include concrete text-block templates for edge-loop request, receipt mail, final result mail, final-result acknowledgement, supervisor reminder, and optional self-mail checkpoint.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `houmao-adv-usage-pattern-skill`: extend the packaged advanced-usage skill with a supported pairwise driver-worker edge-loop pattern and chooser guidance that distinguishes it from the existing forward-relay loop pattern.

## Impact

- Affected spec: `openspec/specs/houmao-adv-usage-pattern-skill/spec.md`
- Affected skill assets: `src/houmao/agents/assets/system_skills/houmao-adv-usage-pattern/SKILL.md` and a new pattern page under `src/houmao/agents/assets/system_skills/houmao-adv-usage-pattern/patterns/`
- Affected validation surface: system-skill packaging and projection tests that assert the advanced-usage skill contents
- No new gateway, mailbox, or manager API surface; this change documents a simpler supported composition over existing messaging, mailbox, and reminder surfaces
