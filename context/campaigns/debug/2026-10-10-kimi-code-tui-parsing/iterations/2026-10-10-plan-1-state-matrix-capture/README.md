# Iteration 1 Test Cases — kimi-code 2.1.1 State Matrix

Test-case specifications for [../2026-10-10-plan-1-state-matrix-capture.md](../2026-10-10-plan-1-state-matrix-capture.md), answering [../../key-questions/KQ-1-signal-survival.md](../../key-questions/KQ-1-signal-survival.md).

## Format: promptfoo

Both session files are **promptfoo-format configs** (`TestSuiteConfig`, schema `https://promptfoo.dev/config-schema.json`; source reference `extern/orphan/promptfoo/src/types/index.ts:1306-1463`). Conformance notes:

- **Provider**: `python:drivers/tui_driver.py:call_api` — promptfoo's documented custom Python provider contract (`extern/orphan/promptfoo/site/docs/providers/python.md`). The provider implementation is campaign tooling written at execution time; it receives the rendered prompt plus `context.vars` and returns a dict (`output`, `metadata`, `latencyMs`).
- **`prompts`**: the schema requires the key, so a placeholder prompt is declared; the provider ignores prompt text and drives `vars.ops`. This is the standard pattern for script providers whose behavior is data-driven.
- **`vars.ops`**: arbitrary JSON is valid `VarsSchema` (types/index.ts:907-917); timed operation sequences live there.
- **Assertions**: real `python` type with `file://` references, following promptfoo's assertion-script return contract (`pass` / `score` / `reason` / `named_scores` / `component_results`). Gate vs measure is expressed in the scripts' return contract, not in schema extensions: **gates** return `pass: false` on integrity breaches (plan gates G1–G3); **measures** always return `pass: true` and report detector-agreement as `named_scores`, because in iteration 1 a detector mismatch is the finding, not a test failure.
- **`evaluateOptions.maxConcurrency: 1`**: cases are sequential legs of one recorded session per file; serial execution is required. Runs always use `--no-cache` (script providers cache on prompt+vars, which would break side-effecting drivers).

## Ops vocabulary

Tracker-blind actions only (per `houmao-dev-tui-testing` record rules): `type_text` (no submit), `submit_text`, `send_key` (with optional `repeat`), `wait_seconds` (fixed holds), `wait_for_pattern` and `wait_for_absence` (documented literal surface pattern present/absent), `catalog_operation` (resolve a reviewed op verbatim from `scripts/demo/shared-tui-tracking-demo-pack/long-horizon/suite.json` by `"<procedure>:op<NN>"`). Every op has a unique `name` and a `meaning` recorded separately from any raw pattern, so later UI wording changes stay visible. The `{{SAFE}}` token in catalog texts expands with the suite's `safe_prefix`. Never use detector-owned waits (`wait_for_ready`, `wait_for_active`).

## Timing constants (UC-04 at 5 fps)

Capture interval 0.2 s. Ready window: ≥ max(0.5 s, 2× interval) = 0.5 s → ≥3 contiguous samples. Post-turn idle gap before the next submit: ≥ max(2.0 s, 4× interval) = 2.0 s → ≥10 samples.

## Files

- [session-1-lifecycle.yaml](session-1-lifecycle.yaml) — unattended `--auto` launch over a fresh untrusted Boltons copy; turn-lifecycle states (trust modal, idle, editing, busy phases, tool/edit workflow, queue, interrupt, compaction, exit).
- [session-2-operator-surfaces.yaml](session-2-operator-surfaces.yaml) — manual permission mode over a trusted Boltons copy; operator-interaction states (bash/write approvals, plan review, AskUserQuestion dialog).
- [asserts/README.md](asserts/README.md) — assertion contracts (inputs, gate/measure behavior, outputs).

## Execution mapping

At execution time the driver: prepares a Boltons copy per session (baseline tag + collection preflight + digests), delegates launch via `houmao-dev-launch-agents`, starts the 5 fps terminal recorder before the first op, drives ops verbatim, stops and freezes; blind labels are then authored, Arm A replay + Arm B escape audit run, and the assertion contracts are evaluated over the replay-vs-labels comparison. These YAML files are the predeclared contract; results land in `../../evidences/`.
