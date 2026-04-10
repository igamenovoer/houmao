## Context

Mailbox-related system skills currently expose three adjacent operator flows:

1. guided project/mailbox setup through `houmao-touring`,
2. mailbox-root and mailbox-account administration through `houmao-mailbox-mgr`,
3. specialist-backed easy launch through `houmao-specialist-mgr`.

Each skill is locally accurate, but the skill family does not currently explain the seams between those flows. In practice that leaves agents to infer how to combine:

- `project mailbox init`,
- `project mailbox register`,
- `agents mailbox register`,
- `project easy profile create` declarative mailbox defaults,
- `project easy instance launch --mail-transport filesystem --mail-root ... [--mail-account-dir ...]`.

The runtime and CLI already have stable behavior for these seams: easy launch derives the default mailbox identity from the managed-agent instance name, safe-registers that address at launch time, and treats `--mail-account-dir` as a private symlink-backed mailbox directory outside the shared root. The design problem is therefore not missing runtime capability; it is missing skill-level guidance about ownership and collision boundaries.

## Goals / Non-Goals

**Goals:**
- Make the skill family describe mailbox setup as distinct lanes instead of one vague setup ceremony.
- Prevent system skills from steering agents into preregistering the same mailbox address that easy launch will later safe-register.
- Make `houmao-specialist-mgr` explicitly distinguish profile-create mailbox fields from launch-time mailbox flags.
- Make `--mail-account-dir` semantics discoverable from the skill pages without requiring the operator to fall back to `--help` or source code.
- Keep the guidance consistent with the existing CLI and runtime contracts.

**Non-Goals:**
- Change the runtime mailbox bootstrap behavior, address derivation rules, or safe-registration semantics.
- Add new CLI flags to `project easy instance launch`, `project mailbox register`, or `agents mailbox register`.
- Redesign mailbox identity defaults, domains, or registration modes.
- Perform a full mailbox docs rewrite outside the system-skill surfaces needed to remove the ambiguity.

## Decisions

### D1: Define mailbox setup as four explicit lanes

The revised skill guidance will frame mailbox-related work as four separate lanes:

1. shared mailbox-root bootstrap,
2. manual mailbox-account registration under a shared root,
3. late mailbox binding for an already-running managed agent,
4. launch-owned mailbox bootstrap for a new easy instance.

Why this approach:
- It matches the existing command ownership model.
- It turns the current implicit distinction into an explicit decision point for agents.
- It avoids overloading "mailbox setup" to mean both root creation and per-address registration.

Alternatives considered:
- Only add warnings to `project mailbox register`.
  Rejected because the problem starts earlier in the tour flow and also appears in specialist launch guidance.
- Move all mailbox-enabled launch guidance into `houmao-agent-instance`.
  Rejected because specialist-backed easy launch is already owned by `houmao-specialist-mgr`, and `houmao-agent-instance` intentionally keeps direct mailbox launch flags out of scope.

### D2: Keep manual registration and launch-owned registration as distinct ownership models

`houmao-mailbox-mgr` will describe `project mailbox register` as manual account administration for standalone addresses, shared team addresses, operator-facing inboxes, or other addresses not being created implicitly by a same-root easy launch. It will explicitly defer existing-agent mailbox association to `agents mailbox ...` and new easy-instance mailbox association to `project easy instance launch`.

Why this approach:
- It preserves the current mailbox skill boundary instead of flattening mailbox admin and instance launch into one skill.
- It addresses the highest-cost operator mistake directly: preregistering the same `<agent-name>@houmao.localhost` address that launch will own.

Alternatives considered:
- Teach `project mailbox register` as the default preparatory step for all filesystem mailbox use.
  Rejected because it is false for the common specialist-backed easy-launch case.

### D3: Put launch collision guidance directly into the specialist launch action

The specialist launch action will explicitly state:

- launch-time filesystem support accepts only the documented launch flags,
- profile-create declarative mailbox fields such as `--mail-address` and `--mail-principal-id` do not exist on `project easy instance launch`,
- the managed-agent instance name seeds the default filesystem mailbox identity when launch-owned mailbox binding is enabled,
- omitting `--mail-account-dir` means launch-owned in-root mailbox bootstrap,
- `--mail-account-dir` is a private directory outside the shared root that is symlinked into the root,
- preregistering the same address can make safe launch fail.

Why this approach:
- The launch action is where the agent chooses the command shape.
- The missing information is not about mailbox administration in general; it is specifically about how easy launch behaves.

Alternatives considered:
- Rely on the CLI reference and quickstart as the only place that explains these details.
  Rejected because the system-skill action pages are the maintained decision surface for the agent workflow.

### D4: Use short interaction blocks instead of broad duplicated tutorials

Each affected skill page will gain a compact interaction-oriented block rather than a long mailbox tutorial. The block will answer:

- what this surface owns,
- what neighboring surface owns the adjacent step,
- what collision or invalid combination to avoid.

Why this approach:
- It adds the missing decision data without turning action pages into duplicate manuals.
- It reduces drift risk by keeping the new content focused on boundaries and collisions.

Alternatives considered:
- Copying the full CLI help or quickstart explanation into every action page.
  Rejected because it would be noisy and harder to maintain.

## Risks / Trade-offs

- [Skill pages become longer and more repetitive] → Keep the new material narrowly focused on ownership boundaries, absent flags, and collision cases.
- [Boundary text can drift from CLI behavior later] → Anchor the wording to current documented CLI contracts and add or update tests that assert the key phrases in the packaged skill assets.
- [Operators may expect docs outside the skills to be updated too] → Keep system-skill clarifications in scope first and note broader doc alignment as follow-up work if remaining confusion persists.

## Migration Plan

1. Update the relevant skill requirements in OpenSpec and implement the skill-asset wording changes.
2. Refresh any system-skill tests that assert packaged content.
3. Verify the packaged skill output still routes to the same command families while now making the lane distinctions explicit.
4. If adjacent docs remain misleading after the skill refresh, queue a follow-up docs-focused change rather than broadening this change during implementation.

## Open Questions

- None at proposal time. The runtime and CLI behavior to document is already established; the remaining work is to encode that behavior clearly in the skill contracts and packaged wording.
