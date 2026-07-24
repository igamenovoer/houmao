---
name: houmao-dev-behavior-testing
description: Use when a Houmao maintainer explicitly needs to qualify whether packaged system skills activate, remain inactive, select the correct actor route, preserve identity and target posture, or enforce their contracts in real admin or managed-agent contexts.
skill_invocation_notation: >
  Top-level skill entrypoints use SKILL.md. Parent-scoped subskill entrypoints use
  SKILL-MAIN.md and are loaded explicitly through their parent; nested SKILL.md is
  accepted only as legacy input when SKILL-MAIN.md is absent.
  Skill and subskill entrypoints use bare object paths: `X` invokes skill X and
  `X->Y->Z` invokes subskill Z. Subcommands use parenthesized components:
  `X->cmd()` invokes a direct subcommand, `X->Y->cmd()` invokes a subcommand of
  subskill Y, and `X->parent()->child()` invokes child subcommand child exposed
  by parent subcommand parent. Intermediate subcommands act as object generators.
  Forms such as `X()` and `X->Y()` are invalid for skill or subskill entrypoints.
---

# Houmao Development Behavior Testing

## Overview

Qualify observable Houmao system-skill behavior in fresh live-agent contexts through selectable functional-area, driver-invocation-mode, and coverage-profile slices. Keep committed selection and case oracles, raw evidence, adjudication, and aggregate results separate so provider nondeterminism remains visible instead of being averaged into a pass.

## When to Use

Use this skill for manual development qualification of direct `$skill` invocation, automatic actor-entrypoint discovery, deliberate non-activation, actor-specific routing, informational and operational phases, identity and target gates, selective shared-routine loading, delegated or direct loop access, or generated notifier/mailbox prompts.

Do not use it for deterministic package structure checks, ordinary Houmao operation, system-skill implementation changes, or TUI tracked-state ground truth. Use `$houmao-dev-tui-testing` when the oracle is TUI tracking rather than system-skill behavior.

## Workflow

When this skill is invoked, execute the following steps in order.

1. **Select the public subcommand** from **Subcommands**. With no actionable task, select `help`.
2. **Resolve exact cases or suite selectors** from [references/case-catalog.md](references/case-catalog.md), then load only the selected functional-area pages plus the shared contracts they need. With no selector, return the read-only area/mode/profile summary.
3. **Plan and freeze the run** with `plan-run`, including driver invocation mode, stimulus origin and digest, initial and delegated root oracles, provider, context, skill revision, repetitions, allowed effects, and evidence sources.
4. **Execute fresh attempts** with `execute-case`. Use the exact stimulus without revealing the expected answer to the agent under test.
5. **Collect immutable observable evidence** with `collect-evidence`; never request or preserve hidden reasoning.
6. **Adjudicate dimensions independently** with `adjudicate-case`, then aggregate all configured attempts with `report-run`.
7. **Report and clean up**. Lead with stable pass, flaky, stable fail, inconclusive, or behavior-pass/activation-unobserved status and retain every evidence path.

If the task does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from the selected case, fixture boundary, evidence contract, verdict rubric, and subcommands, then execute the plan.

## Invocation Contract

These are skill subcommands, not shell commands. Preferred forms are `$houmao-dev-behavior-testing use <subcommand> ...` and `$houmao-dev-behavior-testing <case-or-task>`. Internal designators include `houmao-dev-behavior-testing->run-case()` and `houmao-dev-behavior-testing->adjudicate-case()`.

## Subcommands

### Procedural Subcommands

| Subcommand | Use For | Detail |
| --- | --- | --- |
| `plan-run` | Resolve and freeze suite selectors, invocation modes, cases, variants, root oracles, providers, contexts, repetitions, drift checks, and the run manifest | [commands/plan-run.md](commands/plan-run.md) |
| `execute-case` | Launch one fresh attempt, submit the exact stimulus, and stop at the declared observation boundary | [commands/execute-case.md](commands/execute-case.md) |
| `adjudicate-case` | Assign activation, routing, actor, gate, effect, and outcome verdicts from frozen evidence | [commands/adjudicate-case.md](commands/adjudicate-case.md) |
| `report-run` | Aggregate attempt verdicts without majority-vote masking and finalize cleanup evidence | [commands/report-run.md](commands/report-run.md) |

### Helper Subcommands

| Subcommand | Use For | Detail |
| --- | --- | --- |
| `snapshot-context` | Record secret-free source, skill, pack, provider, fixture, and runtime authority facts | [commands/snapshot-context.md](commands/snapshot-context.md) |
| `collect-evidence` | Freeze native skill events, transcripts, commands, file/runtime deltas, and final response | [commands/collect-evidence.md](commands/collect-evidence.md) |

### Misc Subcommands

| Subcommand | Use For | Detail |
| --- | --- | --- |
| `list-cases` | Summarize areas and profiles or expand selected slices without launching a provider or mutating runtime state | This entrypoint and [references/case-catalog.md](references/case-catalog.md) |
| `run-case` | Execute the full procedure for one case and provider selection | [commands/run-case.md](commands/run-case.md) |
| `run-suite` | Execute a selected catalog slice with fresh attempts and one aggregate report | [commands/run-suite.md](commands/run-suite.md) |
| `help` | Explain contexts, cases, evidence limits, verdicts, and subcommands without launching anything | This entrypoint |

## Reference Map

Load shared contracts only when the selected subcommand needs them:

- [references/case-schema.md](references/case-schema.md): resolved case fields and inheritance.
- [references/fixture-contexts.md](references/fixture-contexts.md): isolated admin, managed-agent, missing-dependency, and lifecycle contexts.
- [references/artifact-contract.md](references/artifact-contract.md): run and attempt layout, immutability, and cleanup.
- [references/evidence-contract.md](references/evidence-contract.md): acceptable evidence and activation visibility.
- [references/verdict-rubric.md](references/verdict-rubric.md): dimensional and aggregate verdict rules.

Load only the functional-area pages selected by an ordinary case or suite:

- [references/cases/activation.md](references/cases/activation.md)
- [references/cases/managed-bootstrap.md](references/cases/managed-bootstrap.md)
- [references/cases/admin-routing.md](references/cases/admin-routing.md)
- [references/cases/managed-agent-routing.md](references/cases/managed-agent-routing.md)
- [references/cases/shared-routines.md](references/cases/shared-routines.md)
- [references/cases/loops.md](references/cases/loops.md)
- [references/cases/generated-prompts.md](references/cases/generated-prompts.md)
- [references/cases/agent-definitions.md](references/cases/agent-definitions.md)

## Calls to External Skills

- Invoke `$houmao-dev-launch-agents` for raw Claude Code, Codex, or Kimi Code admin-context sessions. Consume its verified tmux target and secret-free launch provenance; do not reproduce its credential or launcher resolver.
- Use supported `houmao-mgr` managed launch or join surfaces for managed-agent cases so the agent pack, auto skill, effective prompt, and self-identity authority are genuine.
- Invoke `$terminal-recorder-workflow` only when a terminal recording materially strengthens behavioral evidence. Tracker output remains outside the behavior oracle.
- Invoke `$houmao-dev-tui-testing` separately when the same scenario also needs TUI-state qualification; never merge its tracker verdict into the behavior verdict.

## Help Contract

Explicit help and `list-cases` are read-only. With no selector, explain the eight functional areas, manual, automatic, and not-applicable invocation modes, four cumulative coverage profiles, canonical selector forms, profile counts, supported live providers, fresh-context requirement, evidence visibility limits, five aggregate outcomes, and the difference from TUI testing. Expand case ids and variants only for supplied selectors. Do not preflight credentials, inspect active agents, create a run root, or launch a provider.

## Guardrails

- DO NOT run a case against a maintainer's active project, ordinary tool home, or non-disposable managed agent.
- DO NOT infer `all/normal` or another executable suite when no selector is supplied.
- DO NOT use a coverage profile to choose providers or repetitions.
- DO NOT report generated-prompt or lifecycle stimuli as automatic driver invocation.
- DO NOT report delegated shared or loop roots as directly implicit initial roots.
- DO NOT expose the semantic oracle, required behavior, or forbidden behavior to the agent under test.
- DO NOT infer native skill activation from final prose when root-selection evidence is unavailable.
- DO NOT inspect, request, record, or grade hidden chain-of-thought.
- DO NOT mutate frozen stimuli, context snapshots, or raw evidence after adjudication begins.
- DO NOT use majority vote to hide an intermittent actor, identity, mutation, or activation failure.
- DO NOT modify a packaged system skill because a behavior case fails; report the candidate defect for a separate change.
- DO NOT use current TUI tracker output as behavior-test ground truth.
