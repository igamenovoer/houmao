## Context

The current shadow parser stack already separates provider TUI parsing into `raw_text`, `normalized_text`, `dialog_text`, surface assessment, and caller-owned answer association. That separation is directionally correct, but several code paths and docs still make `dialog_text` sound like reliable clean-text extraction rather than what it really is: a best-effort heuristic rendering of a messy interactive surface.

The stack is also too rigid internally. Today each provider parser owns projection through embedded methods such as `_build_dialog_projection()` and per-line cleanup helpers. That means projection changes for one provider/version/output family require editing the parser class itself rather than swapping a targeted processor implementation. Given how much TUI behavior varies across versions, that rigidity makes parser maintenance fragile.

This matters because the current in-tree consumers are not all using the projection for the same reason:

- `_TurnMonitor` only needs a coarse “projection changed” signal for lifecycle completion.
- Interactive demo inspect uses projected text as an operator-facing tail surface.
- Mailbox parsing is machine-important, but its actual correctness contract comes from sentinel-delimited JSON rather than from generic projection fidelity.

The existing specs say projection is not the authoritative final answer for the last prompt, but they stop short of saying that projection also does not guarantee exact recovered text. The repo therefore needs a clearer reliability model that preserves projection’s legitimate uses while steering important downstream behavior toward schema-shaped outputs and explicit caller-owned extraction.

The core CAO runtime already resolves `shadow_only` by default for supported CAO-backed Claude and Codex sessions. The remaining inconsistency is above that layer: some CLI/help text, maintainer docs, demo packs, report verifiers, and test helpers still behave as if `cao_only` extracted answer text or `done.message` reply text were the normal success contract. As more repo workflows rely on the shadow parser, those surfaces become misleading or brittle.

## Goals / Non-Goals

**Goals:**

- Define `dialog_projection` as a best-effort heuristic rendering rather than an exact recovered transcript.
- Refactor projection logic into modular swappable processor instances so provider/version-specific cleanup can change without rewriting a monolithic parser class.
- Preserve shadow projection as a useful runtime surface for lifecycle diffing, inspection, and best-effort caller-side pattern matching.
- Make reliable downstream machine use depend on schema-shaped prompt/result contracts and explicit extractor logic instead of on projection fidelity.
- Make repo-owned CAO workflows, demos, docs, and incidental test helpers shadow-first by default for tools with runtime shadow parser support, while keeping `cao_only` as an explicit advanced/debug override where intentionally supported.
- Audit and revise affected runtime modules and docs so their wording matches the intended contract.

**Non-Goals:**

- Guarantee exact TUI transcript recovery across redraws, provider versions, or drifted layouts.
- Reintroduce parser-owned “final answer extraction” as a shadow-mode runtime guarantee.
- Add raw tmux scrollback as a new primary caller-facing contract surface.
- Replace runtime-owned structured protocols such as mailbox with free-form projection parsing.
- Ship arbitrary plugin discovery or unbounded third-party code loading for projectors; this change only needs a controlled swappable processor architecture.

## Decisions

### Decision: Refactor provider projection into swappable processor instances

The parser stack should treat dialog projection as a modular provider-owned processor concern rather than as a hardcoded helper method inside each parser class.

The refactor will introduce a shared projector abstraction with these properties:

- one selected processor instance owns projection for one parsed snapshot,
- processor selection is provider-aware and version-aware, and may also consider output-variant evidence,
- the selected processor emits the provider-specific `DialogProjection` subtype plus provenance via `projector_id`, and
- runtime lifecycle code such as `_TurnMonitor` remains unchanged because it still consumes the same `DialogProjection` contract.

Provider parser classes will remain responsible for preset resolution, supported/unsupported detection, and surface assessment, but they will stop owning all projection cleanup logic directly. Instead they will orchestrate selection and invocation of the matching projector.

For maintainability and controlled extensibility, provider parsers or the shared stack should also allow explicit processor injection/override for tests and advanced callers. This is enough to make processor swapping real without committing to a general-purpose plugin-loading system.

**Alternatives considered**

- Keep monolithic parser classes and only add more preset data: rejected because rule churn would still require editing the parser methods themselves and would remain brittle across TUI drift.
- Fully decompose providers into many tiny independently swappable components for preset detection, surface classification, and projection: rejected for now because it increases scope too much; projection modularity is the pressure point that needs relief first.
- Add arbitrary runtime plugin loading from user-provided module paths: rejected because it creates safety and deployment complexity beyond the current need.

### Decision: Keep the current `DialogProjection` payload shape, but redefine its reliability boundary explicitly

The existing field set is already the right shape:

- `raw_text` for original snapshot text,
- `normalized_text` for ANSI-stripped normalized snapshot text, and
- `dialog_text` for dialog-oriented cleanup.

The problem is not missing fields; it is missing reliability language. We will therefore keep the payload shape stable and revise the contract:

- `normalized_text` is the closer-to-source surface.
- `dialog_text` is a best-effort heuristic projection.
- Neither field implies prompt-associated answer ownership by itself.

This avoids wire-format churn while making the intended semantics explicit, even while the producer architecture underneath becomes modular.

**Alternatives considered**

- Rename `dialog_text` to a more obviously heuristic name now: rejected because it creates broad payload churn without solving the core issue that callers need a reliability model, not just a different field name.
- Collapse `normalized_text` and `dialog_text` into one field: rejected because callers genuinely need both a closer-to-source surface and a cleaned operator-facing surface.

### Decision: Define three reliability tiers for shadow-mode text surfaces

The design will distinguish these uses:

1. Lifecycle/runtime tier: projection is acceptable for coarse change detection and readiness/completion logic.
2. Operator/diagnostic tier: projection is acceptable for human-facing summaries such as inspect output.
3. Machine-critical tier: important downstream parsing must rely on schema-shaped prompt/result contracts plus explicit extractor logic over available surfaces, not on generic projection fidelity.

This is the key architectural clarification. It explains why `_TurnMonitor` can continue using projection diffs while mailbox-style protocols need stronger prompt/result contracts.

**Alternatives considered**

- Treat all shadow-mode text uses as equally reliable: rejected because lifecycle diffing and operator inspection tolerate approximation, while downstream machine parsing does not.
- Ban all downstream parsing over shadow payloads: rejected because caller-owned extractors over schema-shaped outputs are still useful and sometimes necessary.

### Decision: Keep runtime-owned structured protocols, but make their reliability come from schema contracts rather than projection semantics

Mailbox is the model case. It already asks the session to return exactly one sentinel-delimited JSON object. That explicit contract is the real correctness boundary. The revised design will say so directly.

Affected runtime-owned machine protocols should follow the same pattern:

- the prompt constrains the agent output shape,
- the parser searches for explicit sentinels or schema-shaped payloads,
- and projection remains only one possible transport surface through which the contract is recovered.

For important parsing, the runtime may inspect more than one available shadow surface, but it must not claim that `dialog_projection.dialog_text` alone is exact.

**Alternatives considered**

- Treat mailbox parsing as an exception and leave the rationale implicit: rejected because the repo is already showing the pattern we want others to follow.
- Promote raw tmux output to a first-class machine contract: rejected because it encourages brittle downstream parsing and undercuts the existing projection/contract separation.

### Decision: Repo-owned CAO workflows for supported tools are shadow-first by default

For tools that have a runtime-owned shadow parser family, repo-owned CAO workflows should follow the runtime's shadow-first posture instead of preserving a mixed-mode mental model.

Concretely:

- repo-owned docs, demos, and helper workflows should either omit parsing-mode overrides and rely on the existing `shadow_only` default or request `shadow_only` explicitly when being explicit is clearer,
- repo-owned helpers and tests should not default to `cao_only` when parsing mode is incidental rather than the subject under test,
- `cao_only` remains supported as an explicit expert/debug/troubleshooting path and for dedicated CAO-native coverage, and
- successful shadow-mode workflows that need text beyond completion status must use protocol-specific verification, side-effect checks, schema/sentinel contracts, or clearly labeled best-effort shadow extraction instead of assuming the final runtime `done.message` is the actual reply text.

This decision also applies to repo-owned helper code that parses live shadow snapshots outside the main turn engine. Such helper code should prefer the shared stack-level shadow abstraction so projector selection, version handling, and controlled overrides stay centralized while the parser stack becomes more modular.

**Alternatives considered**

- Keep repo-owned docs/demos/tests in a mixed-mode posture and rely on local maintainer knowledge to remember that shadow is already the real default: rejected because it keeps producing fragile or misleading consumers.
- Force every repo-owned workflow to pass `--cao-parsing-mode shadow_only` explicitly: rejected because runtime already resolves that default for supported tools and many workflows are clearer when they rely on the shared default instead of duplicating it everywhere.

### Decision: Reframe interactive demo inspect as a best-effort diagnostic surface

The demo’s `--with-output-text` option is useful, but it is not a reliable data-extraction API. The design will keep the field for operator inspection while revising the contract and wording from “clean output text” to “best-effort projected dialog tail”.

That keeps the demo useful without teaching callers the wrong lesson about projection fidelity.

**Alternatives considered**

- Remove the inspect output tail entirely: rejected because it remains valuable for debugging.
- Keep current wording: rejected because it overstates reliability and conflicts with the clarified projection contract.

## Risks / Trade-offs

- [Some existing callers may already assume `dialog_text` is exact] -> Mitigation: make the revised contract explicit in specs, developer docs, reference docs, and affected CLI/demo wording; audit in-tree consumers during implementation.
- [Projector modularity could leak into runtime lifecycle logic] -> Mitigation: keep `DialogProjection` stable and keep `_TurnMonitor` consuming only the shared projection contract.
- [Provider code could still become rigid if projector selection is hardcoded in one place] -> Mitigation: require explicit processor-selection boundaries and constructor-level override points for tests and controlled advanced use.
- [Repo-owned demos or helper scripts may keep treating `done.message` as reply text even after shadow becomes the default posture] -> Mitigation: update spec-owned demo/report contracts, convert helper code to shadow-aware extraction or side-effect validation, and flip incidental test defaults away from `cao_only`.
- [Best-effort wording may feel weaker to operators] -> Mitigation: preserve the existing cleaned surfaces and diagnostic value while being explicit about what they are for.
- [Schema-shaped prompting still runs through messy TUIs] -> Mitigation: require explicit sentinels or compact structured payloads and let caller-owned extractors choose the most suitable text surface (`normalized_text` or `dialog_text`).
- [Refactoring projectors and hardened mailbox/result extraction may add implementation complexity] -> Mitigation: keep the projector abstraction narrowly focused on projection only, and keep machine parsing centered on explicit sentinel/schema contracts rather than on new parser families.

## Migration Plan

1. Revise the affected specs so the contract clearly distinguishes best-effort projection from reliable extraction and requires modular projector selection in the parser stack.
2. Introduce the shared projector abstraction and provider/version-aware processor selection path while preserving the existing `DialogProjection` payload contract.
3. Refactor Claude and Codex projection code into swappable processor implementations and route provenance through `projector_id`.
4. Update runtime/parser docs and module wording to describe `dialog_text`, demo inspect output, and supported CAO workflow posture in shadow-first best-effort terms.
5. Audit repo-owned demos, report verifiers, and helper scripts that still scrape `done.message` or default to `cao_only`, and convert them to shadow-aware success criteria or explicit exceptions.
6. Audit in-tree consumers and keep only the usages that fit the intended reliability tier.
7. For machine-critical flows, preserve or harden schema-shaped prompt/result contracts and explicit extraction helpers.
8. Update tests so they validate processor swapping, revised contract language, shadow-first workflow defaults, and downstream consumer behavior rather than overclaiming projection exactness.

## Open Questions

- Should the controlled projector override live at `ShadowParserStack` construction, provider parser construction, or both?
- Should the runtime add a shared helper for extracting sentinel/schema-shaped payloads from multiple shadow text surfaces, or should each protocol keep its own extractor?
- Should the interactive demo keep the `output_text_tail` field name for compatibility while changing only its wording, or should a later change rename it to something more obviously diagnostic?
