## Context

Houmao now has packaged loop skills for pairwise and relay run control, plus the lower-level execution patterns that those skills compose, but it does not yet provide a packaged system skill for the earlier operator workflow where the operator authors one reusable loop bundle in a user-designated directory and later hands those artifacts to participants without relying on agent-local Houmao runtime directories.

The requested skill needs to cover three related concerns:

- authoring: turn a user's loop intent into one structured operator-owned bundle with a canonical human entrypoint and a small set of readable support documents,
- distribution preparation: describe what each participant should receive and what the operator must confirm before starting the run,
- runtime handoff: prepare one run-charter template and route later live execution to the existing pairwise or relay runtime skills without claiming a new execution engine.

The important current constraints are:

- the user wants the authored loop bundle stored in a user-designated directory rather than in Houmao agent-local runtime or memory directories,
- the operator wants the bundle to be easier to write and review in natural language than a highly segmented policy-file approach,
- the authoritative machine-shaped artifacts should use TOML rather than YAML, but only where fields are simple and unambiguous,
- artifact distribution to managed agents remains the operator's responsibility rather than a built-in planner-side messaging action,
- pairwise and relay execution semantics already exist and should not be replaced,
- the bundle must remain static and operator-owned rather than mixing profile data with mutable run ledgers or per-session retry state,
- the final plan still needs a Mermaid graph that shows the operator outside the execution loop, the master role, the execution topology, and the supervision, completion, and stop checkpoints.

This change is a packaged skill and spec change. It does not add a new loop scheduler, mailbox contract, gateway API, or manager endpoint.

## Goals / Non-Goals

**Goals:**

- Define a packaged `houmao-loop-planner` system skill for authoring operator-owned loop bundles and preparing runtime handoff artifacts.
- Require one canonical bundle layout rooted at a user-designated directory with `plan.md` as the human entrypoint.
- Make Markdown the primary authored format for participant responsibilities, execution rules, and distribution instructions.
- Keep TOML only for low-ambiguity identifiers and run-handoff metadata such as `profile.toml` and `charter.template.toml`.
- Make participant-local responsibilities explicit without forcing the operator to maintain one TOML file per participant or one separate policy file per concern.
- Keep the authored bundle static and separate from mutable runtime state or agent-local install state.
- Prepare runtime handoff templates that route later activation to the existing `houmao-agent-loop-pairwise` or `houmao-agent-loop-relay` skill based on the chosen loop kind.

**Non-Goals:**

- Sending artifacts to agents directly
- Writing into `HOUMAO_JOB_DIR`, `HOUMAO_MEMORY_DIR`, or other agent-local Houmao directories as part of planning
- Starting, monitoring, or stopping live loop runs from `houmao-loop-planner`
- Replacing the existing pairwise or relay runtime skills with a new generic runtime controller
- Defining mutable per-run ledgers, retry counters, or mailbox bookkeeping formats

## Decisions

### Provide one packaged skill with authoring, distribution, and handoff lanes

The implementation should add one packaged system skill named `houmao-loop-planner` with local pages for:

- authoring or revising the loop bundle,
- rendering the final graph and writing the bundle artifacts,
- preparing participant and distribution guidance,
- preparing runtime handoff templates and routing guidance.

Why:

- The requested workflow is about authoring and preparing artifacts before a live run begins.
- Keeping distribution preparation and runtime handoff inside the same packaged skill keeps the operator-facing workflow coherent while still stopping before live execution.

Alternative considered:

- Extending `houmao-agent-loop-pairwise` and `houmao-agent-loop-relay` to absorb the bundle-authoring workflow. Rejected because those skills already center on loop-kind-specific run control, while this change is an earlier, operator-owned planning layer that should remain generic across loop kinds.

### Support one simplified bundle form only

`houmao-loop-planner` should always write a directory bundle rather than supporting multiple authored forms.

The bundle should use this canonical layout:

```text
<user-designated-loop-dir>/
  plan.md
  participants.md
  execution.md
  distribution.md
  profile.toml
  runs/
    charter.template.toml
```

Why:

- The loop still needs more than one file, but the operator should be able to understand and edit the whole bundle without navigating a forest of micro-policy files.
- A canonical directory shape keeps distribution and revision predictable while staying human-readable.

Alternative considered:

- Keeping the earlier highly segmented bundle with participant TOML files, separate policy TOML files, and per-agent packet manifests. Rejected because it makes ordinary planning heavier than necessary and over-optimizes for machine structure over operator readability.

### Use Markdown as the primary authored surface and TOML only for simple metadata

`plan.md`, `participants.md`, `execution.md`, and `distribution.md` should be human-facing Markdown with required section structure. `profile.toml` and `runs/charter.template.toml` should be the only required TOML artifacts.

Why:

- The operator explicitly asked to simplify the bundle and use natural language where possible.
- Markdown is a better fit for instructions, responsibilities, and nuanced execution guidance.
- TOML remains useful for stable identifiers, enums, and short lists that benefit from predictable parsing.

Alternative considered:

- Keeping participant responsibilities and policy modules in TOML. Rejected because those sections are richer in prose than in machine-shaped fields and become cumbersome when over-structured.

### Keep the bundle operator-owned and separate from agent-local runtime state

The planner should write only into the user-designated bundle directory. It should not install files under agent-local Houmao runtime or memory paths and should not define mutable run ledgers inside the bundle.

Why:

- The user explicitly wants the bundle to exist first as operator-owned planning material.
- This avoids conflating static authored policy with mutable runtime scratch or durable session state.

Alternative considered:

- Having the planner immediately materialize agent-local copies or runtime ledgers. Rejected because distribution is intentionally an operator responsibility and because mutable run state belongs to later runtime execution, not planning.

### Make participant and execution views explicit in Markdown

`participants.md` should contain one clearly marked section per participant. Each participant section should capture at minimum:

- agent identity and role,
- who the agent receives work from,
- who the agent reports to,
- which other agents it may call,
- required artifacts,
- required message types,
- escalation conditions,
- forbidden actions.

`execution.md` should describe the shared loop behavior, including:

- the loop kind and topology summary,
- the message flow,
- what the master does,
- how status is summarized,
- how completion is evaluated,
- how stop is handled.

`distribution.md` should describe:

- what the operator should send to each participant,
- which acknowledgements or confirmations to expect,
- what must be true before starting,
- which existing runtime skill to use next.

Why:

- The user explicitly wants to tell each agent what it has, who it may call, and how it participates in the loop.
- The operator also wants those rules to be easy to read and easy to revise without juggling many tiny files.

Alternative considered:

- Relying only on one global plan file. Rejected because participant responsibilities, loop behavior, and operator distribution guidance are distinct enough to deserve separate documents even in the simplified bundle.

### Route runtime handoff by loop kind to existing loop runtime skills

The planner should require one explicit `loop_kind` such as `pairwise` or `relay` in `profile.toml`. The handoff lane should prepare one `charter.template.toml` file and tell the operator which existing runtime skill owns live execution next:

- `pairwise` -> `houmao-agent-loop-pairwise`
- `relay` -> `houmao-agent-loop-relay`

`houmao-loop-planner` should not define its own live `start`, `status`, or `stop` control API.

Why:

- Pairwise and relay already have different execution semantics and existing packaged runtime skills.
- Keeping runtime activation delegated avoids introducing a second orchestration engine with overlapping responsibilities.

Alternative considered:

- Letting `houmao-loop-planner` also start and supervise live runs itself. Rejected because it would duplicate the existing runtime-control skills and blur the separation between planning and execution.

### Require a top-level Mermaid graph in `plan.md`

The final bundle should require a Mermaid graph embedded in `plan.md`. The top-level graph should show:

- the operator outside the execution loop,
- the designated master role,
- the high-level execution topology for the chosen loop kind,
- the supervision loop,
- where completion is evaluated,
- where stop is evaluated.

Why:

- The graph is part of the operator-facing planning artifact, not an optional flourish.
- The bundle must stay readable to both the operator and downstream participants.

Alternative considered:

- Splitting the top-level graph into a separate required file. Rejected because `plan.md` should remain the canonical entrypoint and repo guidance already prefers Mermaid embedded in the main document.

## Risks / Trade-offs

- [The bundle format is heavier than a single-file plan] -> Mitigation: keep `plan.md` as the concise canonical entrypoint and limit required support files to three focused Markdown documents plus two small TOML files.
- [Manual operator distribution can drift from the authored bundle] -> Mitigation: make `distribution.md` explicit about who receives what and require stable profile identifiers and versions in the bundle.
- [Runtime skills may diverge from the planner's assumptions over time] -> Mitigation: keep runtime handoff explicit by loop kind and avoid embedding duplicate execution protocols inside `houmao-loop-planner`.
- [Natural-language guidance can become inconsistent without structure] -> Mitigation: require fixed section headings and minimum content expectations inside `participants.md`, `execution.md`, and `distribution.md`.

## Migration Plan

1. Add the new capability spec for `houmao-loop-planner-skill`.
2. Add a packaged system skill directory under `src/houmao/agents/assets/system_skills/houmao-loop-planner/`.
3. Implement authoring-lane guidance for bundle creation, revision, Markdown section conventions, small TOML schema references, and Mermaid graph rendering.
4. Implement distribution-lane guidance for `participants.md`, `execution.md`, and `distribution.md`.
5. Implement handoff-lane guidance for `charter.template.toml` preparation and loop-kind routing to the existing pairwise or relay runtime skills.
6. Update system-skill packaging and content tests to assert that the new skill is packaged and that its guidance covers the simplified bundle structure, Markdown-first authoring, minimal TOML artifacts, operator-managed distribution, and runtime handoff.

Rollback is low risk: remove the new packaged skill assets, revert the new capability spec, and revert the corresponding packaging and content tests.

## Open Questions

- None for artifact generation. This design intentionally keeps distribution operator-managed, keeps most authored meaning in Markdown, and delegates runtime activation to the existing loop runtime skills.
