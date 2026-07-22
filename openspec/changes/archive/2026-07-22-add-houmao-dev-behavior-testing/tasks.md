## 1. Rename the TUI Qualification Skill

- [x] 1.1 Move `skillset/dev/houmao-dev-testing` to `skillset/dev/houmao-dev-tui-testing` without dropping any command, reference, or metadata file.
- [x] 1.2 Update the renamed skill frontmatter, title, invocation contract, metadata, default prompt, and common-mistake wording to the `houmao-dev-tui-testing` identity while preserving the existing workflow.
- [x] 1.3 Replace current TUI qualification default roots and tracked examples from `tmp/houmao-dev-testing/` to `tmp/houmao-dev-tui-testing/`.
- [x] 1.4 Verify the renamed skill still exposes `record`, `label`, `replay`, `compare`, `render-video`, `run-all`, and `help` and still delegates provider launch to `houmao-dev-launch-agents`.

## 2. Create the Behavior Qualification Skill Router

- [x] 2.1 Initialize `skillset/dev/houmao-dev-behavior-testing` with `SKILL.md`, `agents/openai.yaml`, `commands/`, and `references/` using repository and skill-creator conventions.
- [x] 2.2 Author the concise Imsight-style top-level workflow, invocation contract, complex-procedure subcommand tables, context/evidence boundaries, external-skill calls, help contract, and guardrails.
- [x] 2.3 Add procedural command pages for `plan-run`, `execute-case`, `adjudicate-case`, and `report-run` with predecessor and output contracts.
- [x] 2.4 Add helper command pages for `snapshot-context` and `collect-evidence` and misc pages for `run-case` and `run-suite`.
- [x] 2.5 Generate matching OpenAI metadata with explicit-only invocation and a behavior-qualification default prompt.

## 3. Define Behavior Artifacts and Verdicts

- [x] 3.1 Add the case schema with stable identity, context, stimulus, semantic oracle, evidence, repetition, timeout, effect, and cleanup fields.
- [x] 3.2 Add fixture-context guidance for isolated admin sessions, genuine managed-agent sessions, provider applicability, fixture credentials, and secret-safe launch provenance.
- [x] 3.3 Add the run artifact contract for frozen manifests, attempt directories, immutable raw evidence, adjudication records, reports, and cleanup state.
- [x] 3.4 Add the evidence contract with provider-native activation priority, observable fallback sources, hidden-reasoning exclusion, and raw-evidence immutability.
- [x] 3.5 Add the dimensional verdict and aggregate rubric, including three-attempt defaults and stable, flaky, failed, inconclusive, and activation-unobserved outcomes.

## 4. Add the Committed Case Catalog

- [x] 4.1 Add the catalog index with a version, case ids, families, contexts, activation modes, default repetitions, and direct links to every family page.
- [x] 4.2 Add activation/bootstrap cases for welcome, unrelated work, explicit-only roots, explicit root selection, and auto-prompt startup and reload.
- [x] 4.3 Add admin cases for help, welcome delegation and handoff, shared routing, target ambiguity, ineligible routes, spoof resistance, and joined-session adoption.
- [x] 4.4 Add managed-agent cases for help, fresh identity checks, identity failure, self and peer targets, ineligible routes, and spoof resistance.
- [x] 4.5 Add shared-routine cases for direct actor selection, inherited frames, selective loading, aliases, eligibility, missing loop siblings, and manifest route coverage.
- [x] 4.6 Add loop cases for manual-only activation, explicit pro and lite selection, help, inherited actor frames, direct admin default, and leading `as-agent`.
- [x] 4.7 Add generated-prompt cases for notifier rounds, ordinary mailbox work, missing dependencies, and actor-pack mismatch wording.

## 5. Update Development Guidance and Add Validation Coverage

- [x] 5.1 Update `skillset/dev/README.md` to distinguish behavior qualification, TUI tracker qualification, raw provider launch, and terminal recording.
- [x] 5.2 Add focused tests that validate both skill identities, OpenAI metadata, command/reference links, required case families and ids, verdict vocabulary, removal of the old root, and exclusion from the runtime manifest.
- [x] 5.3 Add a focused assertion that every current admin and agent manifest route has a committed shared-route coverage row or explicit unsupported marker.
- [x] 5.4 Scan current tracked development and qualification material for stale active `houmao-dev-testing` invocations or default roots and repair them without rewriting historical artifacts.

## 6. Verify the Change

- [x] 6.1 Run the skill-creator validator on both development testing skills; require the TUI skill to pass and validate the behavior skill's Imsight notation with focused coverage because the generic validator rejects that optional extension key.
- [x] 6.2 Run the focused development-skill tests and relevant existing system-skill tests.
- [x] 6.3 Run Markdown-sensitive formatting checks, repository lint, and `git diff --check`.
- [x] 6.4 Run `openspec validate add-houmao-dev-behavior-testing --strict` and mark every completed task accurately.
