## Context

Houmao already ships direct-operation and manager-style system skills for project overlays, mailbox administration, specialist/profile authoring, managed-agent lifecycle, messaging, gateway control, and mailbox participation. Those skills are intentionally narrow and keep routing boundaries explicit, but first-time users still have to infer the bigger workflow: how to initialize a project, whether mailbox is optional, how specialists differ from live agents, what to do after launch, and how `stop`, `relaunch`, and `cleanup` differ.

The new `houmao-touring` skill is meant to close that gap without collapsing the current architecture. It needs to behave like a revisitable guided tour rather than a one-shot onboarding wizard. The user may already have a project, mailbox, specialists, profiles, or running agents; after any branch they may want to return, create more specialists, launch more agents, or move into prompt, watch, mail, reminder, stop, relaunch, or cleanup flows. Because this is a packaged system skill, the design also needs to fit the current packaged catalog, install-state model, docs inventory, and system-skill tests.

## Goals / Non-Goals

**Goals:**
- Add a packaged Houmao-owned `houmao-touring` system skill under the maintained runtime asset root.
- Make `houmao-touring` a manual-invocation-only guided tour that is explicit about being for first-time or re-orienting users.
- Keep the touring flow state-aware and non-linear: inspect current state, explain posture, present likely next branches, and allow revisiting branches after each action.
- Cover the full guided-tour surface requested by the user:
  - project overlay setup and explanation,
  - project-local mailbox setup,
  - specialist and optional profile creation,
  - easy-instance launch,
  - post-launch prompt / gateway watch / mailbox / reminder entry,
  - instance stop / relaunch / cleanup follow-up.
- Require example-driven, informative questions when the touring skill needs user input.
- Keep direct-operation ownership on the existing packaged skills and command families.
- Update catalog, install inventory, docs, and tests so the new skill is a first-class packaged skill.

**Non-Goals:**
- Add a new CLI command family or a new runtime control surface just for touring.
- Replace `houmao-project-mgr`, `houmao-mailbox-mgr`, `houmao-specialist-mgr`, `houmao-agent-instance`, `houmao-agent-messaging`, `houmao-agent-gateway`, or `houmao-agent-email-comms`.
- Encode touring behavior in Python logic beyond the existing packaged-skill asset, catalog, and test/doc inventory updates.
- Force users through a linear wizard or require all branches to complete before useful work can continue.
- Auto-run destructive operations such as cleanup after stop.

## Decisions

### Decision: `houmao-touring` will be a meta-skill that composes existing Houmao skills

`houmao-touring` will follow the same broad architectural pattern as `houmao-adv-usage-pattern`: the skill itself is the entry index, but the concrete command execution remains owned by the existing maintained skills. The touring skill will:

- inspect current posture through maintained Houmao manager commands,
- explain what already exists,
- choose the next branch with the user,
- route the requested work to the correct Houmao-owned skill and command family.

This avoids duplicating command shapes across yet another `SKILL.md` and preserves the current ownership lines.

Alternatives considered:
- Put every command shape directly into `houmao-touring`.
  Rejected because it would duplicate and eventually drift from the maintained direct-operation skills.
- Replace one of the existing manager skills with a broader “getting started” version.
  Rejected because the current narrow boundaries are useful and already documented.

### Decision: Touring is manual-invocation-only, but still a normal packaged system skill

Manual invocation is a usage rule, not an installation rule. The skill will be packaged, projected, and documented like the other Houmao-owned skills, but its top-level instructions and `agents/openai.yaml` prompt will explicitly say to use `houmao-touring` only when the user explicitly asks for the touring experience or equivalent first-time guided help.

This keeps the skill available anywhere Houmao installs its packaged system skills while preventing it from hijacking ordinary direct-operation requests.

Alternatives considered:
- Keep the skill out of normal packaged installation and require explicit `--skill houmao-touring` installs.
  Rejected because it would make the guided tour unavailable in the common places where first-time users are likely to ask for help.

### Decision: Add a dedicated `touring` named set in the packaged catalog

`houmao-touring` is not a direct-operation skill and does not fit cleanly inside `user-control`, `advanced-usage`, or the lifecycle/messaging/gateway sets. The packaged catalog will therefore gain a dedicated `touring` named set that contains only `houmao-touring`.

The fixed packaged default selections will include that `touring` set so the skill is present in the same packaged environments where the rest of the Houmao-owned skill surface already appears. Because the skill is manual-only, broader installation does not create routing ambiguity.

Alternatives considered:
- Put `houmao-touring` into `user-control`.
  Rejected because `houmao-touring` is a guided cross-surface entrypoint rather than a direct user-control management skill.
- Leave `houmao-touring` ungrouped and available only by explicit skill name.
  Rejected because it makes the packaged inventory and default install explanation harder to reason about.

### Decision: The tour starts with state inspection, not with “Step 1”

The top-level touring flow will first orient on current state using maintained commands such as:

- `houmao-mgr project status`,
- project mailbox status or accounts inspection when relevant,
- specialist/profile listing,
- `houmao-mgr agents list`,
- `houmao-mgr agents state`,
- `houmao-mgr agents gateway status`,
- `houmao-mgr agents mail resolve-live`.

From that state, the skill will explain the current posture in plain language and offer likely branches. Example branches include:

- initialize or inspect project overlay,
- set up or inspect project mailbox,
- create another specialist,
- create a reusable profile,
- launch another agent,
- prompt or watch a running agent,
- send mailbox messages,
- create reminders,
- stop, relaunch, or clean up a managed agent.

This satisfies the requirement that the tour be revisitable and non-linear.

Alternatives considered:
- Hard-code a single setup order from project init to cleanup.
  Rejected because it fails for users who already have partial state and for users who want to revisit earlier branches.

### Decision: The packaged asset will use branch-oriented supporting pages plus a question-style reference

The new skill tree will use a top-level `SKILL.md` plus local supporting documents for:

- state orientation,
- project and mailbox branch entry,
- specialist/profile and launch branch entry,
- post-launch live-operations branch entry,
- lifecycle branch entry,
- a question-style reference with example-rich input prompts.

The detailed direct-operation semantics will continue to live in the existing skills. The touring pages only need enough local guidance to explain branch selection and handoff boundaries.

Alternatives considered:
- Keep everything inside one long `SKILL.md`.
  Rejected because the tour covers too many branches and would become hard to scan or maintain.

### Decision: Informative user-input prompts are a first-class touring behavior

Whenever `houmao-touring` asks the user for input, the prompt must explain what the requested value means, why it matters, and show realistic examples. Optional branches should offer a recommended default or an explicit skip path when appropriate.

This is especially important for first-time users in places where Houmao vocabulary is non-obvious:

- specialist name,
- mailbox address and principal id,
- whether to create an optional profile,
- which live agent to stop or relaunch,
- whether cleanup means `session` or `logs`.

Alternatives considered:
- Reuse the terse missing-input style from the direct-operation skills.
  Rejected because those prompts optimize for efficient operators, not for first-time orientation.

## Risks / Trade-offs

- [Skill overlap drift] → Keep `houmao-touring` at the routing and explanation layer only, and point detailed execution to the existing skill families.
- [Broad packaged availability could make routing noisy] → Make manual invocation an explicit rule in both `SKILL.md` and `agents/openai.yaml`.
- [State inspection may become too heavyweight] → Limit touring inspection to the maintained high-signal status/list surfaces and avoid deep environment probing or duplicate discovery logic.
- [First-time explanations can become verbose and repetitive] → Centralize question-style guidance in a dedicated local reference and keep direct-operation detail delegated.
- [Catalog/default-set changes expand doc and test churn] → Treat the new skill as a normal packaged inventory change and update catalog, docs, and inventory assertions together.

## Migration Plan

This change is additive. There is no runtime-state or persisted-data migration.

Implementation will:

1. Add the new packaged `houmao-touring` skill asset tree.
2. Add the new skill and dedicated `touring` set to the packaged catalog.
3. Extend the fixed default set lists to include the touring set.
4. Update system-skill installer tests and inventory assertions.
5. Update README and system-skills documentation to describe the new guided-tour skill and its manual-only invocation rule.

Rollback is straightforward: remove the new packaged skill asset tree, remove the catalog entry and set membership, and revert the corresponding docs and tests.

## Open Questions

None. The main behavioral choices for this proposal are settled:

- the skill name is `houmao-touring`,
- the flow is branching rather than linear,
- the skill is manual-invocation-only,
- the tour includes post-launch operations and lifecycle follow-up,
- input prompts are explanatory and example-driven.
