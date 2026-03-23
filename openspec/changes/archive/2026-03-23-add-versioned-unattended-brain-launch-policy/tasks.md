## 1. Launch Policy Inputs And Artifact Plumbing

- [x] 1.1 Add secret-free operator prompt policy fields at `launch_policy.operator_prompt_mode` in recipe/manifests plus `BuildRequest.operator_prompt_mode` in build inputs.
- [x] 1.2 Extend launch-plan and session-manifest models with a typed `LaunchPolicyProvenance` structure for requested mode, detected version, selected strategy, and override source.
- [x] 1.3 Route raw `launch.sh` helpers and runtime-managed launch paths through one shared Python launch-policy application entrypoint while keeping `launch.sh` shell-based, and cover `headless`, `cao_rest`, and `houmao_server_rest`.
- [x] 1.4 Ensure unattended launch requests do not require user-prepared per-tool no-prompt config files; runtime-owned strategy application must be able to synthesize needed provider config/state from minimal credential inputs.

## 2. Versioned Launch Policy Registry

- [x] 2.1 Implement the YAML-backed runtime-owned registry format and loader under `src/houmao/agents/launch_policy/`, including required entry fields for strategy id, policy mode, backends, version range, minimal inputs, evidence, owned paths, and actions.
- [x] 2.2 Implement subprocess-based tool-version detection via the actual executable `--version` output plus strict unattended resolution and the transient `HOUMAO_LAUNCH_POLICY_OVERRIDE_STRATEGY` override.
- [x] 2.3 Implement ordered launch-policy action execution with a canonical generic action vocabulary, provider-hook dispatch, and explicit `launch_args_override` conflict validation for strategy-owned args.
- [x] 2.4 Add strategy metadata for minimal supported inputs, evidence provenance (official docs, source references, and live-probe notes), and strategy-owned runtime paths/keys.

## 3. Provider Strategy Migration

- [x] 3.1 Move existing Codex unattended trust and approval behavior behind registry-backed strategies instead of implicit bootstrap-only logic.
- [x] 3.2 Extend Codex unattended strategy coverage so fresh homes built from `auth.json` or env-only custom-provider credentials (`requires_openai_auth = false`, `wire_api = "responses"`) also suppress current startup-only migration/model prompts where required by the detected version.
- [x] 3.3 Implement Claude registry-backed unattended startup with version-aware settings/state synthesis, custom API-key approval memory, dangerous-mode suppression, workspace-trust seeding for isolated homes, and strategy-declared owned JSON/settings paths.
- [x] 3.4 Surface resolved strategy provenance in runtime diagnostics and persisted metadata for unattended launches.

## 4. Verification And Documentation

- [x] 4.1 Add tests for recipe/build manifest plumbing and launch-policy registry resolution behavior, including unsupported-version failure.
- [x] 4.2 Add provider-focused fresh-home tests for Codex unattended launches starting from `auth.json` or env-only credentials and for Claude unattended launches starting from API-key/env-only credentials with no pre-made prompt-suppression config files.
- [x] 4.3 Add a live validation matrix or equivalent probe workflow that records the current supported-version findings for Codex and Claude against the installed CLIs.
- [x] 4.4 Update runtime, brain, and troubleshooting docs to describe the first-class unattended launch policy, minimal-input contract, typed provenance, env-var override, versioned strategy behavior, and the explicit Gemini deferral.
- [x] 4.5 Update demo workflows that currently rely on ad hoc no-prompt overrides to use the new unattended launch policy explicitly.
