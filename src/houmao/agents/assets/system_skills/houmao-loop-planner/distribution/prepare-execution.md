# Prepare `execution.md`

Use this page when the bundle needs the shared execution guidance written in `execution.md`.

## Workflow

1. State the chosen loop kind explicitly.
2. Summarize the execution topology at the level the operator and participants actually need.
3. Describe the message flow in structured Markdown.
4. Describe what the master does, how status is summarized, how completion is evaluated, and how stop is handled.
5. Keep runtime execution semantics aligned with the later runtime skill instead of inventing a new protocol here.

## Required Sections

`execution.md` should include at minimum:

- `Loop Kind`
- `Topology Summary`
- `Message Flow`
- `Master Procedure`
- `Reporting Posture`
- `Completion Behavior`
- `Stop Behavior`

## Guardrails

- Do not repeat every low-level protocol detail from the runtime execution patterns.
- Do not turn `execution.md` into a machine-shaped policy dump when structured Markdown is enough.
- Do not claim that `execution.md` itself starts the run.
