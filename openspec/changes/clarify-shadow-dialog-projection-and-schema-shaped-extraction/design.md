## Context

The current shadow parser stack already separates provider TUI parsing into `raw_text`, `normalized_text`, `dialog_text`, surface assessment, and caller-owned answer association. That separation is directionally correct, but several code paths and docs still make `dialog_text` sound like reliable clean-text extraction rather than what it really is: a best-effort heuristic rendering of a messy interactive surface.

This matters because the current in-tree consumers are not all using the projection for the same reason:

- `_TurnMonitor` only needs a coarse “projection changed” signal for lifecycle completion.
- Interactive demo inspect uses projected text as an operator-facing tail surface.
- Mailbox parsing is machine-important, but its actual correctness contract comes from sentinel-delimited JSON rather than from generic projection fidelity.

The existing specs say projection is not the authoritative final answer for the last prompt, but they stop short of saying that projection also does not guarantee exact recovered text. The repo therefore needs a clearer reliability model that preserves projection’s legitimate uses while steering important downstream behavior toward schema-shaped outputs and explicit caller-owned extraction.

## Goals / Non-Goals

**Goals:**

- Define `dialog_projection` as a best-effort heuristic rendering rather than an exact recovered transcript.
- Preserve shadow projection as a useful runtime surface for lifecycle diffing, inspection, and best-effort caller-side pattern matching.
- Make reliable downstream machine use depend on schema-shaped prompt/result contracts and explicit extractor logic instead of on projection fidelity.
- Audit and revise affected runtime modules and docs so their wording matches the intended contract.

**Non-Goals:**

- Guarantee exact TUI transcript recovery across redraws, provider versions, or drifted layouts.
- Reintroduce parser-owned “final answer extraction” as a shadow-mode runtime guarantee.
- Add raw tmux scrollback as a new primary caller-facing contract surface.
- Replace runtime-owned structured protocols such as mailbox with free-form projection parsing.

## Decisions

### Decision: Keep the current `DialogProjection` payload shape, but redefine its reliability boundary explicitly

The existing field set is already the right shape:

- `raw_text` for original snapshot text,
- `normalized_text` for ANSI-stripped normalized snapshot text, and
- `dialog_text` for dialog-oriented cleanup.

The problem is not missing fields; it is missing reliability language. We will therefore keep the payload shape stable and revise the contract:

- `normalized_text` is the closer-to-source surface.
- `dialog_text` is a best-effort heuristic projection.
- Neither field implies prompt-associated answer ownership by itself.

This avoids wire-format churn while making the intended semantics explicit.

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

### Decision: Reframe interactive demo inspect as a best-effort diagnostic surface

The demo’s `--with-output-text` option is useful, but it is not a reliable data-extraction API. The design will keep the field for operator inspection while revising the contract and wording from “clean output text” to “best-effort projected dialog tail”.

That keeps the demo useful without teaching callers the wrong lesson about projection fidelity.

**Alternatives considered**

- Remove the inspect output tail entirely: rejected because it remains valuable for debugging.
- Keep current wording: rejected because it overstates reliability and conflicts with the clarified projection contract.

## Risks / Trade-offs

- [Some existing callers may already assume `dialog_text` is exact] -> Mitigation: make the revised contract explicit in specs, developer docs, reference docs, and affected CLI/demo wording; audit in-tree consumers during implementation.
- [Best-effort wording may feel weaker to operators] -> Mitigation: preserve the existing cleaned surfaces and diagnostic value while being explicit about what they are for.
- [Schema-shaped prompting still runs through messy TUIs] -> Mitigation: require explicit sentinels or compact structured payloads and let caller-owned extractors choose the most suitable text surface (`normalized_text` or `dialog_text`).
- [Hardened mailbox/result extraction may add some implementation complexity] -> Mitigation: keep the pattern narrow and reusable, centered on explicit sentinel/schema contracts rather than new parser families.

## Migration Plan

1. Revise the affected specs so the contract clearly distinguishes best-effort projection from reliable extraction.
2. Update runtime/parser docs and module wording to describe `dialog_text` and demo inspect output as best-effort projected text.
3. Audit in-tree consumers and keep only the usages that fit the intended reliability tier.
4. For machine-critical flows, preserve or harden schema-shaped prompt/result contracts and explicit extraction helpers.
5. Update tests so they validate the revised contract language and consumer behavior rather than overclaiming projection exactness.

## Open Questions

- Should the runtime add a shared helper for extracting sentinel/schema-shaped payloads from multiple shadow text surfaces, or should each protocol keep its own extractor?
- Should the interactive demo keep the `output_text_tail` field name for compatibility while changing only its wording, or should a later change rename it to something more obviously diagnostic?
