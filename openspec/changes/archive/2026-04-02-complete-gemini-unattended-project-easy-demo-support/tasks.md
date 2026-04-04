## 1. Gemini unattended launch-policy support

- [x] 1.1 Probe Gemini CLI unattended startup on a fresh managed home to identify the validated lower-bound CLI version, whether zero provider hooks are sufficient, and whether any Gemini-owned startup files are actually required.
- [x] 1.2 Add maintained Gemini unattended strategy coverage for `gemini_headless` in the launch-policy registry using the validated version range and either zero owned paths/hooks or the smallest discovered Gemini-specific startup surfaces/hooks.
- [x] 1.3 Update runtime launch-policy handling and diagnostics so compatible Gemini unattended launches proceed and incompatible Gemini versions or backends still fail closed clearly.
- [x] 1.4 Add regression coverage for Gemini unattended strategy resolution and runtime launch behavior.

## 2. Project-easy Gemini unattended posture

- [x] 2.1 Change `houmao-mgr project easy specialist create --tool gemini` to persist `launch.prompt_mode: unattended` by default while preserving `--no-unattended` as the opt-out to `as_is`.
- [x] 2.2 Keep Gemini specialists headless-only on `project easy instance launch` while aligning stored specialist metadata and generated presets with the new unattended default.
- [x] 2.3 Add or update CLI tests for Gemini easy-specialist default posture, `--no-unattended`, and headless-only launch validation.

## 3. Expand the supported headless gateway demo to Gemini

- [x] 3.1 Add `gemini` to the supported tool set in the demo pack models, CLI argument choices, tracked parameters, and matrix flow.
- [x] 3.2 Extend the demo runtime/auth import path to support the maintained Gemini auth families, use `tests/fixtures/agents/tools/gemini/auth/personal-a-default` as the canonical supported demo fixture, and keep API-key fixture support for manual variation.
- [x] 3.3 Add or update demo-pack tests for the Gemini lane, including supported tool validation, auth import behavior, and matrix coverage.

## 4. Docs and validation

- [x] 4.1 Update the primary maintained docs for this change, especially `scripts/demo/single-agent-gateway-wakeup-headless/README.md`, `scripts/demo/README.md`, `docs/getting-started/easy-specialists.md`, `docs/getting-started/quickstart.md`, and `docs/reference/cli/houmao-mgr.md`, so Gemini is documented as a supported unattended headless lane.
- [x] 4.2 Refresh Gemini unattended validation or smoke guidance in the headless gateway demo README and related operator docs so the canonical OAuth-backed demo lane and its verification expectations are explicit.
