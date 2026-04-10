## Why

Houmao now documents the pairwise edge-loop execution pattern, but it does not yet provide a packaged skill for the higher-level workflow where a user-controlled agent formulates a loop plan, designates one Houmao master agent, and asks that master to keep the run alive across pairwise delegations. Users need one supported skill that turns natural-language intent into a valid pairwise run plan and one control contract for starting, monitoring, and stopping that run without making the user agent part of the loop itself.

## What Changes

- Add a packaged Houmao-owned system skill named `houmao-agent-loop-pairwise` for user-controlled pairwise loop planning and run control.
- Define two lanes inside that skill:
  - an authoring lane that formulates user intent into a pairwise loop plan in one Markdown file or one plan bundle directory,
  - an operating lane that sends `start`, `status`, and `stop` control-plane requests to the designated master agent.
- Require the authoring lane to normalize delegation authority explicitly rather than allowing free delegation by default.
- Require the authoring lane to produce a Mermaid diagram that shows the final loop graph, which agent controls which downstream agents, where the supervision loop lives, and where completion and stop conditions are evaluated.
- Require the operating lane to keep the user agent outside the execution loop and to place liveness ownership on the designated master after the master accepts the run.
- Require `stop` to default to interrupt-first semantics unless the user explicitly requests graceful termination.
- Require the skill to reuse existing Houmao messaging, mailbox, gateway, and pairwise-pattern guidance rather than introducing a new runtime loop engine.

## Capabilities

### New Capabilities
- `houmao-agent-loop-pairwise-skill`: packaged system-skill guidance for formulating pairwise loop plans, rendering the final control graph, and operating a master-owned run through `start`, `status`, and `stop`.

### Modified Capabilities

None.

## Impact

- Affected skill assets under `src/houmao/agents/assets/system_skills/`, including a new packaged skill directory for `houmao-agent-loop-pairwise`
- Affected system-skill packaging and projection tests under `tests/unit/agents/`
- Cross-skill composition with existing Houmao-owned skills, especially `houmao-agent-messaging`, `houmao-agent-gateway`, `houmao-agent-email-comms`, and the pairwise pattern documented by `houmao-adv-usage-pattern`
- No new gateway, mailbox, or manager API surface; this change defines a higher-level controller and plan-authoring skill contract over existing runtime primitives
