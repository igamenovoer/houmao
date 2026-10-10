# Operator Interpretation: swe-critic

## Reading of the Intent

The operator asks for a reusable agent definition named `swe-critic` that reviews a software project's codebase and designs, whether the project is a demo or production-level, for extensibility, ease of understanding, quality of responsibility division, coherence versus coupling, and similar design-quality concerns. All authoring materials live under `examples/agent-authoring/swe-critic`.

## Normalized Decisions

- **Identity**: `definition_id = swe-critic`, `revision_id = 1.0.0`.
- **Role prompt and memo seed**: sourced from `intent/src/prompts/system.md` and `intent/src/memo/houmao-memo.md`, materialized beneath `materials/`. Both bind the required deploy input `task_objective` through the `{{houmao.deploy.task_objective}}` marker.
- **Deploy contract**: one input, `task_objective` (string, required). It carries the concrete review objective for a deployment, including target project context, stated maturity, and emphasis. Maturity calibration lives in the role prompt rather than in a separate enum, because the intent treats "demo or production" as context the critic adapts to, not as a switch that changes the contract.
- **Skills**: one authored skill, `swe-critic-review`, holding the review workflow, reporting contract, and read-only boundary. Copied complete from `intent/src/skills/swe-critic-review`.
- **Instance contract**: no runtime variables and no mindsets. Private workspace is optional, disabled by default, with one materialized `reports/` directory for review output.

## Points Left Unresolved by the Source Intent

Recorded here rather than synthesized into the revision:

- Deploy-time tool, credential, workdir, and model selections are deployment concerns, not definition material, and are deliberately absent.
- Review-depth tuning (for example quick versus deep passes) is not declared; the objective text is expected to carry any depth instruction in this revision.
- Mindset questionnaires are not declared; no per-instance calibration beyond the deploy objective exists.
- Whether the critic may propose patches (rather than only report) is left to the operator at prompt time; the definition default is read-only review.

## Fidelity Statement

No requirements beyond the supplied intent were invented. The four review dimensions, the demo-versus-production calibration, and the evidence-backed reporting posture come directly from the source overview; structure (deploy input, skill, workspace contract) is the minimal machinery needed to make the intent deployable.
