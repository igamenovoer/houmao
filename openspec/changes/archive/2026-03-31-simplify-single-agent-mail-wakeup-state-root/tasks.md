## 1. Root Layout And State Resolution

- [x] 1.1 Change the demo path helpers and persisted-state discovery to use one canonical `scripts/demo/single-agent-mail-wakeup/outputs/` root instead of `outputs/<tool>/`.
- [x] 1.2 Update follow-up command resolution so normal stepwise commands use canonical persisted state and no longer require tool-specific `--demo-output-dir` during documented usage.
- [x] 1.3 Update command output and report/inspect payloads to describe the selected tool as persisted state rather than as part of the output-root path contract.

## 2. Persistent Overlay And Fresh-Run Reprovisioning

- [x] 2.1 Split demo reprovision behavior into preserved overlay-backed specialist state versus resettable run-local state.
- [x] 2.2 Preserve reusable specialist-defining overlay content across fresh runs, including project-easy catalog, managed content, easy metadata, and generated agent-definition projections.
- [x] 2.3 Reset mailbox state, copied project content, runtime state, logs, deliveries, and evidence on each fresh `start`.

## 3. Workflow And Tooling Adjustments

- [x] 3.1 Update `start --tool claude|codex` so the selected tool is persisted under the canonical root and reused by follow-up commands.
- [x] 3.2 Revise automatic and stepwise workflow logic, including `matrix`, to operate correctly against the canonical root without concurrent per-tool live output directories.
- [x] 3.3 Keep Claude and Codex project-easy setup/auth/specialist flows valid under the shared-root model and document any deterministic naming or reuse rules needed for tool switching.

## 4. Documentation And Verification

- [x] 4.1 Update the demo README and operator-facing examples to teach the canonical `outputs/` root and normal follow-up commands without `--demo-output-dir`.
- [x] 4.2 Update focused unit tests and expected-report fixtures to match the single-root layout and persistent-overlay reset semantics.
- [x] 4.3 Run focused verification for the demo pack, including both supported tools and the updated stepwise/manual command surface.
