## Context

The loop skill already has an editable `intention/` source area and generated `execplan/` package. Mature generated loop plans show recurring patterns that are useful across many tasks: manifest-indexed generated artifacts, structured participant registries, mail schemas and renderers, a minimal state kernel, a plan-local harness, event/tick skills, and a runtime audit directory. These patterns should become defaults so users do not need to rediscover the same loop infrastructure for each new task.

The defaults must remain flexible. The maintained skill should define generic scaffolding posture, while task objectives, topology, role count, scoring, evidence rules, and domain records remain derived from intention source and clarification decisions.

## Goals / Non-Goals

**Goals:**

- Add concise default generation guidance for workspace contracts, execplan package contents, participants, communications, runtime state, harness surfaces, generated skills, agent bindings, and run artifacts.
- Keep generated defaults overrideable by explicit intention source.
- Route workspace mechanics, mail transport, managed-agent lifecycle, memory, gateway, and inspection through maintained Houmao skills.
- Document the defaults in developer design notes so later maintainers can extend the skill consistently.

**Non-Goals:**

- Do not impose any concrete participant topology.
- Do not add domain-specific policy, objective, evidence, scoring, or record tables.
- Do not replace existing Houmao mail, workspace, gateway, lifecycle, or messaging skills.
- Do not add a runtime implementation beyond generated-loop guidance and documentation in this change.

## Decisions

1. Treat defaults as a scaffold profile, not fixed generated content.

The skill should describe the default layers and file families a useful loop normally needs, but the generator may omit irrelevant pieces for simple loops and extend them for complex loops. This keeps the defaults lightweight while giving authors a complete target shape.

Alternative considered: require every generated loop to include the full mature package shape. That would reduce ambiguity but overfit simple loops and make the skill less useful for non-stateful or small participant workflows.

2. Keep policy and dynamic values outside static skill prose.

Scheduling policy, participant routes, state invariants, and objective constraints should live in generated `specs/` files and be queried through the harness or generated docs. Static role skills should describe how to look up and apply those contracts, not embed per-loop constants.

Alternative considered: place common policies directly in generated event skills. That would make first generation easier, but later execplan updates and clarification would be harder because policy would be duplicated across skills.

3. Use a minimal state kernel as the default for stateful mail loops.

When a loop has durable handoffs or cross-agent bookkeeping, the generated state model should start from generic tables or equivalent records for plan metadata, process state, handoffs, email payloads, operator intent events, and generic events. Domain tables are extensions owned by the generated loop.

Alternative considered: avoid state defaults and rely on mail history only. That preserves simplicity, but makes validation, recovery, scheduler decisions, and audit harder for most multi-agent loops.

4. Keep generated harness responsibilities narrow.

The harness should validate, render, query, explain, and apply loop-local records through controlled commands. It should not own mailbox delivery, agent launch, workspace creation, or gateway discovery.

Alternative considered: make the harness a full loop runner. That would centralize control but duplicate maintained Houmao operation surfaces and blur ownership.

## Risks / Trade-offs

- Default scaffold feels too large for small loops -> Mitigate by wording defaults as expected reusable patterns that may be omitted when the intention clearly does not need them.
- Agents overfit to a reference topology -> Mitigate by naming generic roles such as coordinator, worker, and reviewer only as examples, and requiring topology to come from intention or clarification.
- Static skill text drifts from generated contracts -> Mitigate by requiring generated skills to query specs/harness for policy, state, and dynamic values.
- Generated harness overlaps platform skills -> Mitigate by documenting the boundary: harness owns loop-local data mechanics; maintained Houmao skills own platform operations.
