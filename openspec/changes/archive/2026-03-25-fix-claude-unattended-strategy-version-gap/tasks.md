## 1. Repair Claude unattended strategy coverage

- [x] 1.1 Update launch-policy strategy models/parsing so policies declare supported versions with dependency-style range expressions, then migrate the Claude registry entries to that format.
- [x] 1.2 Validate the maintained Claude unattended startup assumptions for the target supported version window and update `src/houmao/agents/launch_policy/registry/claude.yaml` with the correct supported-version declaration or new strategy entry.
- [x] 1.3 Add regression coverage for strict strategy selection so maintained `raw_launch` and `claude_headless` versions resolve successfully by declared supported-version range while unsupported versions still fail closed with version-aware errors.

## 2. Fix runtime-managed override and diagnostics

- [x] 2.1 Update runtime launch-plan composition so `HOUMAO_LAUNCH_POLICY_OVERRIDE_STRATEGY` is honored from the caller process environment during policy resolution without persisting the override into manifests or requiring env-contract projection.
- [x] 2.2 Improve runtime-managed/local `houmao-mgr agents launch` error reporting so unattended strategy compatibility failures clearly identify the requested policy, detected Claude version, resolved backend surface, and that provider startup never began.

## 3. Add operational guardrails

- [x] 3.1 Add local managed-launch coverage for both interactive and headless Claude unattended paths so launch-policy compatibility failures are distinguished from backend-selection or provider-startup regressions.
- [x] 3.2 Add a maintained Claude drift guardrail that validates the declared supported-version ranges for the maintained unattended path, and run the relevant lint, typecheck, and test commands for the touched launch-policy/runtime surfaces.
