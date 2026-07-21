## Context

Houmao packages six standalone public system skills, sixteen parent-scoped shared routines, and one separately managed auto-system-prompt skill. Deterministic tests validate manifests, installation topology, prompt text, frontmatter, and static routing markers, but they cannot establish whether Claude Code, Codex, or Kimi Code actually selects the expected skill in a live context. Provider behavior is nondeterministic, native skill-call evidence differs by host, and exact prose assertions would reject semantically correct runs.

The current `skillset/dev/houmao-dev-testing` skill solves a different problem. It records agent TUIs, freezes raw evidence, supports independent public-state labeling, replays the current tracker at varied cadences, compares the tracker with ground truth, and renders review videos. Its broad name now obscures that boundary.

The development skillset already provides `houmao-dev-launch-agents` for raw provider launch and `terminal-recorder-workflow` for terminal evidence. Managed-agent behavior cases must instead use supported Houmao launch or join surfaces so the agent pack, auto skill, effective system prompt, and self-identity authority match production design. Development skills are repository-only authoring aids and do not belong to the packaged system-skill manifest.

## Goals / Non-Goals

**Goals:**

- Add a manual development skill for repeatable live qualification of system-skill activation, non-activation, route selection, actor posture, gates, and visible outcomes.
- Commit the test definitions as reviewable Markdown rather than generate them from the runtime manifest at execution time.
- Accept provider-specific wording while making wrong actor selection, skipped identity checks, forbidden mutation, and improper loop activation hard failures.
- Keep evidence and adjudication separate enough that missing native skill-call telemetry cannot be mistaken for proof of activation.
- Rename the existing TUI qualification skill and its development-facing paths without changing its operational meaning.
- Follow the Imsight command-skill layout: concise router, numbered workflows, dedicated command pages, progressively loaded references, object-style invocation notation, and sparse negative guardrails.

**Non-Goals:**

- Change the meaning, activation metadata, route map, or implementation of any packaged system skill or generated runtime prompt.
- Turn live behavioral cases into deterministic unit tests or require a single exact transcript.
- Inspect or preserve hidden chain-of-thought.
- Add provider login automation, copy credentials into reports, or test against a maintainer's active project or managed agents.
- Make `houmao-dev-behavior-testing` or `houmao-dev-tui-testing` part of an admin or agent pack.
- Keep a compatibility `houmao-dev-testing` skill after the rename.

## Decisions

### 1. Split Behavioral Qualification from TUI Tracker Qualification

Create `skillset/dev/houmao-dev-behavior-testing` and rename `skillset/dev/houmao-dev-testing` to `skillset/dev/houmao-dev-tui-testing`. The new skill judges agent decisions and effects in designed contexts. The renamed skill continues to judge tracked TUI state against independent raw evidence.

This split gives each skill one oracle. A behavioral run may retain a terminal recording, but it does not consult tracker output to decide whether a system skill behaved correctly. A TUI qualification run may drive an agent task, but it does not claim that a system skill activated merely because the final behavior looked plausible.

Keeping one broad skill with two modes was rejected because its evidence boundaries, artifacts, and failure interpretations would conflict. Creating a compatibility wrapper was rejected because repository policy permits breaking development changes and the old name is the ambiguity being removed.

### 2. Use an Imsight Complex-Procedure Skill with No Subskills

The behavior skill exposes procedural subcommands `plan-run`, `execute-case`, `adjudicate-case`, and `report-run`; helper subcommands `snapshot-context` and `collect-evidence`; and misc subcommands `list-cases`, `run-case`, `run-suite`, and `help`. Each non-trivial subcommand owns a page below `commands/`. The top-level entrypoint uses standard object-style notation and explicitly disables implicit invocation in `agents/openai.yaml`.

All case families share the same context, artifact, evidence, and verdict contracts, so they remain references owned by the top-level skill. They are not subskills and do not receive `SKILL-MAIN.md`. Detailed cases live in `references/cases/*.md`, with every case family linked directly from `SKILL.md` to preserve progressive disclosure.

A collection-of-routines layout was rejected because execution depends on predecessor artifacts: a frozen plan and context precede execution, execution evidence precedes adjudication, and attempt verdicts precede aggregation.

### 3. Commit a Versioned, Explicit Case Catalog

`references/case-catalog.md` is the catalog authority. It lists every case id, family, context, activation mode, default repetitions, and family detail page. Family pages cover activation/bootstrap, admin routing, managed-agent routing, shared routines, loops, and generated prompts. The first version includes the cases agreed during exploration, including negative activation and actor-spoofing cases.

Each case declares its exact stimulus and semantic oracle. The schema records applicable providers, installed pack, auto-skill posture, fixture state, expected root and delegated route, required and forbidden observables, permitted effects, evidence requirements, timeout, repetitions, and cleanup. The runtime manifest may be inspected to detect catalog drift, but the skill does not synthesize new live cases from it.

Dynamic case generation was rejected because a changed manifest could silently rewrite the test oracle in the same revision being tested.

### 4. Separate Context, Evidence, and Verdict Artifacts

Every run uses a fresh `tmp/houmao-dev-behavior-testing/<run-id>/` root and a frozen `run-manifest.json`. Each `(case, provider, attempt)` receives an isolated directory containing the exact stimulus, a secret-free context snapshot, provider-native skill events when available, transcript or terminal evidence, observed commands, bounded filesystem/runtime before-and-after evidence, and an attempt verdict.

Raw admin-context provider sessions delegate launch to `houmao-dev-launch-agents` and use an isolated project-local or provider-home skill projection. Managed-agent cases use Houmao's supported managed launch/join path so the agent pack, auto skill, prompt, and identity command remain genuine. Fixture credentials follow repository testing guidance, and reports record only bundle identifiers and non-secret provenance.

Evidence priority is provider-native skill-call telemetry, then exact command/file/runtime observations, then visible response semantics. The skill never treats hidden reasoning as evidence. If the provider does not expose root selection, the activation dimension remains `unobservable` even when the downstream behavior passes.

### 5. Use Dimensional and Aggregate Verdicts

Each attempt records `pass`, `fail`, `incomplete`, or `unobservable` for activation, routing, actor, gates, effects, and outcome. A required forbidden behavior is an immediate failure in its dimension. Exact wording, harmless ordering differences, and equivalent presentation remain allowed unless a case declares the text itself authoritative.

Default qualification repeats each case three times in fresh sessions. Aggregation reports `stable-pass`, `flaky`, `stable-fail`, or `inconclusive`. When all observable behavioral dimensions pass but native activation evidence is unavailable, the aggregate may report `behavior-pass-activation-unobserved`; it is not a full activation qualification. Reports preserve every attempt and never average failures into a pass.

A single boolean and majority-vote pass were rejected because both hide the reason for nondeterminism and can certify intermittent actor or mutation failures.

### 6. Preserve the TUI Skill by Targeted Rename

Move the entire existing skill directory, change only development-facing identity and path wording, and retain the six current subcommands, predecessor gates, evidence separation, state-labeling vocabulary, comparison contracts, video contracts, and external launch dependency. Rename the default run root from `tmp/houmao-dev-testing/` to `tmp/houmao-dev-tui-testing/` in the skill and TUI qualification documentation.

The implementation uses source comparison and focused assertions to ensure the renamed skill still exposes `record`, `label`, `replay`, `compare`, `render-video`, `run-all`, and `help`, and still routes provider launch to `houmao-dev-launch-agents`.

### 7. Validate Structure without Running Live Provider Cases

Repository tests validate both skill roots, frontmatter names, metadata, subcommand/resource links, case ids, case-family coverage, verdict vocabulary, absence of the old skill root, and absence from the packaged system-skill manifest. The skill-creator validator and repository formatting/lint checks validate authoring structure.

The generic skill-creator validator does not currently admit Imsight's optional top-level `skill_invocation_notation` key. The behavior skill retains that required extension and focused repository coverage compares it with the standard value used by packaged Imsight-formatted system skills. Generic validation remains authoritative for the renamed TUI skill and for all frontmatter rules it can evaluate; its extension-only rejection is recorded rather than "repaired" by deleting required metadata.

This change does not execute the live case catalog automatically. Live runs require external provider credentials, consume model resources, and may mutate disposable runtime fixtures. The new skill itself is the maintained manual qualification procedure.

## Risks / Trade-offs

- [Provider-native skill-call telemetry may be absent or change shape] → Keep activation separate from behavioral dimensions and report it as unobservable rather than infer it from prose.
- [Live agents remain nondeterministic] → Use fresh sessions, at least three default attempts, immutable raw evidence, and explicit flaky aggregation.
- [Behavior cases could affect a real project or tool home] → Require disposable workdirs, isolated skill projections, fixture credentials, bounded before/after evidence, and cleanup obligations.
- [The committed case catalog may drift from the runtime route map] → Add structural coverage tests and a planning preflight that compares catalog expectations with the current manifest without generating or rewriting cases.
- [The TUI rename may break saved development prompts] → Treat the rename as intentional and update all tracked invocations and temporary-root examples in one change.
- [A large catalog could overload skill context] → Keep the router compact and load only the chosen family and case contract.
- [The generic skill validator rejects Imsight extension metadata] → Retain the standard notation key, validate its exact value with focused repository coverage, and record the upstream validator limitation.

## Migration Plan

1. Create the new behavior-testing skill and its committed references and command pages.
2. Move the existing TUI skill directory and update its identity, metadata, invocations, and artifact-root references with targeted substitutions.
3. Update tracked TUI qualification documentation and development skill guidance to use the new name.
4. Add focused structural tests and validate both skill roots, links, catalogs, and packaged-skill exclusion.
5. Run OpenSpec validation, skill validation, focused tests, formatting, lint, and repository diff checks.

Rollback restores the old directory name and tracked development references and removes the new development skill. No runtime installation, receipt, managed home, or public system-skill migration is involved.

## Open Questions

None. The initial live provider matrix is Claude Code, Codex, and Kimi Code because those are the providers supported by the development launcher. A case records unsupported or unobservable provider posture explicitly rather than claiming coverage.
