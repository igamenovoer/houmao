# Execplan Step By Step

## Read First

- `../reference/scaffold-surface.md`
- `../reference/generation-pipeline.md`
- `../reference/generated-contract-defaults.md`
- `../reference/topology-modes.md`
- `../reference/cycle-normalization.md`
- `../reference/predecessor-context.md`
- `../reference/mail-schema-events.md`
- `../reference/result-routing.md`
- MUST READ: `../reference/runtime-mail-model.md`
- `../reference/platform-boundaries.md`

## Preconditions

- User wants generated execution material with guided decisions.
- Current intention source exists.
- The user accepts an interactive flow where one decision question may pause generation.

## Inputs

Require:
- `<loop-dir>`
- `<loop-dir>/intention/README.md`
- `<loop-dir>/intention/loop-overview.md`

Read:
- relevant files under `<loop-dir>/intention/`
- accepted intention ADRs under `<loop-dir>/adrs/` when present
- existing `<loop-dir>/execplan/` material when updating or resuming the stepwise generation
- existing `<loop-dir>/execplan/adrs/*.md` when present

## Outputs

Generate all execplan artifacts through the standard staged order, but allow the user to decide generation choices one question at a time:

```text
execplan-stepwise-shell
  -> execplan-specs-process
      -> execplan-specs-contract
          -> execplan-harness
              -> execplan-skills
                  -> execplan-agent-bindings
                      -> execplan-finalize
                          -> validate-execplan
```

Record accepted generation decisions under:

```text
<loop-dir>/execplan/adrs/0001-short-decision-slug.md
<loop-dir>/execplan/adrs/0002-short-decision-slug.md
```

`execplan/adrs/` is part of generated execplan material. It records decisions about generated artifact shape, defaults, omissions, bindings, harness surfaces, communication contracts, validation posture, or other execplan implementation choices. It does not replace editable intention source.

## Decision Areas

Ask only when a decision materially affects generated artifacts and cannot be derived from intention source, accepted intention ADRs, existing execplan ADRs, or documented defaults:
- which optional execplan layers should be generated or explicitly omitted;
- topology mode, tree-loop cycle normalization, generic cycle control, and result-routing posture when source intent leaves them open;
- generic predecessor-context choices when a downstream participant may need selected upstream refs or summaries;
- participant instance naming and generated skill naming when collisions or ambiguity are likely;
- message family names, request/reply links, or renderer section choices not clear from intention source;
- state, record, run artifact, or audit scope when the loop can reasonably choose more than one compact model;
- harness command surface, relative-path or symlink posture, and command envelope choices;
- agent binding details such as notifier prompt customization, generated skill installation, memo seed policy, or workspace policy;
- final docs and manifest omissions when a default layer is intentionally absent.

Do not ask about ordinary defaults that the skill already defines, such as mail as the default participant handoff transport, notifier-prompt-driven mail processing, flat generated skill directories, or the canonical process overview path.

## Actions

1. Confirm `<loop-dir>` and required intention files exist.
2. Use the packaged scaffold generator with the `execplan-stepwise-shell` profile before asking artifact-generation questions. That profile owns:
  - the standard `execplan/` directory shell;
  - `execplan/adrs/`;
  - the provisional `manifest.toml` seed.
3. Start at the earliest missing or affected stage.
4. For the active stage, read current upstream artifacts and existing `execplan/adrs/`.
5. If a material generation decision is unresolved, ask exactly one focused question.
6. Include a recommended answer when context supports one, and name the artifacts that will change if accepted.
7. Stop after asking the question and wait for the user's answer.
8. After the user accepts or edits the decision:
  - write one ADR under `execplan/adrs/`;
  - update or generate the affected execplan artifacts immediately;
  - update manifest or validation notes when the decision records an omission or accepted equivalent.
9. Continue to the next unresolved decision or next staged generation step.
10. After all stages complete, run or request `validate-execplan`.

## Execplan ADR Shape

Use sequential numeric filenames scoped to `execplan/adrs/`:

```text
<loop-dir>/execplan/adrs/0001-short-decision-slug.md
```

Create each ADR from the packaged `execplan-adr` scaffold profile or the shared template asset under `assets/scaffolds/execplan/adrs/execplan-adr.md.tmpl`, then fill the required sections:
- `Status`
- `Stage`
- `Context`
- `Decision`
- `Affected Artifacts`
- `Consequences`

Rules:
- Keep ADRs concise and artifact-focused.
- Record only accepted decisions.
- Do not create ADRs for routine defaults that did not require a user decision.
- If a question reveals that editable intent is wrong or incomplete, tell the user to run `clarify-intent` or explicitly update `intention/`; do not silently move source-of-truth intent into `execplan/adrs/`.

## Question Style

- Ask one decision question, not a checklist.
- Include:
  - the decision question;
  - a recommended answer when context supports one;
  - the stage being generated;
  - affected artifacts;
  - whether downstream stages will be regenerated.

Good shape:

```text
Question: For generated worker-result mail, should the reply family include a structured `evidence_refs` field, or should evidence be captured only through a separate record apply command?

Recommended answer: Include `evidence_refs` in the reply payload and let the harness validate referenced evidence records separately.
That keeps the mail readable while preserving compact evidence bookkeeping in records.

If accepted, I will record `execplan/adrs/0003-worker-result-evidence-link.md`, update `specs/comms/`, and rerun harness and skill generation downstream.
```

## Constraints

- Do not perform platform launch, mailbox delivery, gateway, memory, lifecycle, or workspace creation side effects.
- Do not ask multiple questions at once.
- Do not treat an ADR as accepted until the user accepts or edits the decision.
- Do not use `execplan/adrs/` for user-editable intent decisions that belong in `intention/` and `<loop-dir>/adrs/`.
- Do not leave generated artifacts inconsistent with accepted execplan ADRs.
