## Why

Houmao now documents the forward relay-loop execution pattern, but it does not yet provide a packaged skill for the higher-level workflow where a user-controlled agent describes a goal, the system formulates a relay loop plan with a designated master or loop origin, and that master executes and supervises the run without making the user agent part of the loop itself. Users need one supported skill that turns natural-language intent into a valid relay plan and one control contract for starting, monitoring, and stopping that run over named Houmao agents.

## What Changes

- Add a packaged Houmao-owned system skill named `houmao-agent-loop-relay` for user-controlled relay loop planning and run control.
- Define two lanes inside that skill:
  - an authoring lane that formulates user intent into a relay loop plan in one Markdown file or one plan bundle directory,
  - an operating lane that sends `start`, `status`, and `stop` control-plane requests to the designated master or loop origin.
- Require the authoring lane to normalize route or forwarding authority explicitly rather than allowing free downstream handoff by default.
- Require the authoring lane to produce a Mermaid diagram that shows the final relay graph, who may hand off to whom, where the supervision loop lives, where the final result returns to the origin, and where completion and stop conditions are evaluated.
- Require the operating lane to keep the user agent outside the execution loop and to place liveness ownership on the designated master after the master accepts the run.
- Require `stop` to default to interrupt-first semantics unless the user explicitly requests graceful termination.
- Require the skill to reuse existing Houmao messaging, mailbox, gateway, and relay-pattern guidance rather than introducing a new runtime loop engine.

## Capabilities

### New Capabilities
- `houmao-agent-loop-relay-skill`: packaged system-skill guidance for formulating relay loop plans, rendering the final relay control graph, and operating a master-owned run through `start`, `status`, and `stop`.

### Modified Capabilities

None.

## Impact

- Affected skill assets under `src/houmao/agents/assets/system_skills/`, including a new packaged skill directory for `houmao-agent-loop-relay`
- Affected system-skill packaging and projection tests under `tests/unit/agents/`
- Cross-skill composition with existing Houmao-owned skills, especially `houmao-agent-messaging`, `houmao-agent-gateway`, `houmao-agent-email-comms`, and the relay pattern documented by `houmao-adv-usage-pattern`
- No new gateway, mailbox, or manager API surface; this change defines a higher-level controller and plan-authoring skill contract over existing runtime primitives
