## Context

`houmao-touring` is currently packaged as a manual guided-tour skill, but its branch structure and requirements drift toward broad capability enumeration. That is useful for maintainers, but too much for first-time users. The tour should instead teach Houmao through a staged progression: first create and talk to one agent, then learn live operation and inter-agent coordination, then move into composed loop and workspace systems.

The current packaged skill already routes execution to owning skills and ships self-contained branch/reference pages. The revision should preserve those boundaries while changing how the tour chooses and presents next actions.

## Goals / Non-Goals

**Goals:**

- Make beginner, intermediate, and advanced the organizing model for `houmao-touring`.
- Keep beginner guidance focused on the minimum useful path: tool selection, credentials, project/mailbox basics, specialist, easy profile, launch, and direct communication.
- Move memo, mailbox-driven prompting, inter-agent communication, gateway notifier rounds, and inspection into intermediate guidance that appears after the user has at least one useful agent context.
- Keep loop-lite, loop-pro, and isolated workspace management in advanced guidance.
- Replace generic branch follow-up lists with stage-aware next touring actions.
- Remove stale touring requirements that present retired pairwise or generic loop packages as current choices.

**Non-Goals:**

- Do not turn touring into a full catalog of every packaged system skill.
- Do not add new `houmao-mgr` commands or change CLI behavior.
- Do not move execution ownership from direct-operation skills into `houmao-touring`.
- Do not change system-skill installation sets or catalog membership.
- Do not include unrelated utility workflows, such as LLM Wiki maintenance, in the first-user touring path unless a later product decision explicitly makes them part of Houmao agent orchestration onboarding.

## Decisions

### D1: Use Learning Stages Instead Of Capability Groups

The tour will classify next actions by learner readiness:

- beginner: setup and first agent conversation,
- intermediate: live operation and manual multi-agent coordination,
- advanced: generated loops and isolated workspace management.

Alternative considered: keep the existing branch catalog and add missing entries. That would make the tour more complete as a reference surface, but it would weaken the first-user teaching posture.

### D2: Keep State Orientation, But Map State To Stage-Aware Offers

The orient branch will still inspect project, specialist/profile, running-agent, mailbox, gateway, and relevant live state. Its routing matrix will then offer stage-aware next actions instead of broad branch labels alone.

Alternative considered: make the tour a fixed beginner-to-advanced wizard. That would be easier to narrate but would break the existing requirement that re-orienting users should not be forced back to the beginning.

### D3: Treat Intermediate As The Place For Real Agent Operation

Intermediate guidance will cover memo and pages, direct prompts, mailbox messages, operator-origin mail or prompt injection through mail, gateway mail-notifier behavior, notifier-round processing, and inspection. These concepts are confusing before an agent exists, but they are exactly what a user needs after the first launch.

Alternative considered: leave memo and notifier workflows only in advanced usage. That hides practical day-two behavior behind an overly advanced label.

### D4: Keep Advanced Focused On Coordination Systems

Advanced guidance will route loop work to `houmao-agent-loop-lite` or `houmao-agent-loop-pro`, and workspace isolation to `houmao-utils-workspace-mgr`. Tree-loop and generic-loop remain mode choices inside pro rather than separate retired packages.

Alternative considered: include all optional utilities in advanced. That would drift back into catalog browsing and dilute the specific advanced path for multi-agent orchestration.

### D5: Preserve Owning-Skill Boundaries

`houmao-touring` will explain concepts, choose stage-aware next actions, and route to owning skills. It will not duplicate direct command semantics for credentials, mailbox administration, messaging, gateway, memory, loop execution, workspace execution, or lifecycle management.

Alternative considered: inline more command examples in the tour. That may help in isolated moments, but command drift has already made touring harder to maintain.

## Risks / Trade-offs

- [Users looking for a full function catalog may miss utility skills] -> Keep explicit help text saying touring is an onboarding path, and point users to the system-skills overview or direct skill help for catalog/reference needs.
- [Stage labels could feel too linear for re-orienting users] -> Preserve current-state orientation and allow users to jump stages when they ask directly.
- [Intermediate could become too broad] -> Keep it limited to live operation and manual coordination after an agent exists.
- [Advanced loop terminology may regress to retired pairwise names] -> Remove retired package references from touring requirements and route current loop work only to lite/pro.
