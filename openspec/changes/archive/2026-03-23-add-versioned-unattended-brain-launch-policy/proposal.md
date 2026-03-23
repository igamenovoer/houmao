## Why

Orchestrated agent launches still block on provider-native trust, permission, onboarding, and migration prompts when started from fresh runtime homes, even when the caller only wants minimal credential projection and minimal launch args.

Fresh-home probes on the installed CLIs show that the blocking surfaces are broader than one permission flag:

- Claude Code 2.1.81 stops on theme onboarding, custom API-key approval, bypass-permissions confirmation, and workspace trust unless the runtime home seeds the right mix of `settings.json` and `.claude.json` state.
- Codex CLI 0.116.0 stops on trust with `auth.json` alone, and after trust is seeded it can still stop on a model migration prompt unless runtime-owned notice/model state is also set.

The current fixes are tool-specific and version-fragile, so the same “launch this brain without asking me anything” intent is not expressed or enforced systematically across build, runtime, demos, and CAO-backed flows.

## What Changes

- Add a first-class unattended launch policy that lets callers request a brain/runtime posture where startup operator prompts are forbidden.
- Persist the requested unattended launch policy in brain artifacts under a concrete policy field flow so raw launch helpers, realm-controller sessions, and demo packs can honor the same intent.
- Introduce a versioned launch policy registry under `src/houmao/agents/launch_policy/` that resolves tool- and version-specific prompt-suppression strategies from detected CLI versions instead of hardcoding one static set of flags or config patches.
- Require unattended strategies to work from fresh runtime homes using only minimal credential inputs plus minimal caller launch args; the system may synthesize or override runtime-owned config/state as needed instead of depending on user-prepared per-tool config files.
- Record typed launch-policy provenance plus strategy evidence and validation expectations so documented behaviors and live-observed state patches are distinguishable and auditable per tool version.
- Require unattended launch to fail fast when no compatible strategy exists for the detected tool version instead of falling back silently to a potentially prompt-blocking launch.
- Update Codex unattended startup behavior so fresh homes built from env-only custom-provider credentials or minimal auth inputs can suppress trust, full-access, and model-migration startup prompts without requiring user-managed `config.toml`.
- Update Claude-specific startup behavior so unattended launches can synthesize or patch the version-appropriate settings/state needed to avoid onboarding, custom API-key approval, bypass-permissions confirmation, and workspace trust prompts in isolated `CLAUDE_CONFIG_DIR` homes.
- Keep `gemini_headless` out of v1 unattended strategy coverage explicitly; unattended Gemini launches fail closed until a later follow-up adds registry-backed support.

## Capabilities

### New Capabilities
- `versioned-launch-policy-registry`: Runtime-owned registry and strategy resolution for version-specific unattended launch policy actions.

### Modified Capabilities
- `component-agent-construction`: Brain construction inputs and manifests gain a first-class unattended launch policy request instead of relying on ad hoc tool-specific overrides.
- `brain-launch-runtime`: Launch plan composition and runtime startup honor persisted unattended launch intent and fail fast when the detected tool version lacks a compatible no-prompt strategy.
- `claude-cli-noninteractive-startup`: Claude noninteractive startup becomes version-strategy-driven and covers workspace trust/bootstrap behavior in addition to dangerous-mode prompt suppression.

## Impact

- Affected code: `src/houmao/agents/brain_builder.py`, `src/houmao/agents/launch_policy/`, brain manifest/loading code, launch-plan composition, runtime backends, Claude/Codex bootstrap helpers, and shared demo launch code.
- Affected artifacts: brain recipes/build requests, resolved brain manifests, session launch metadata, runtime-owned home bootstrap behavior, and repo-owned version strategy data.
- Affected docs/tests: agent brain/runtime reference docs, unattended launch troubleshooting guidance, official-doc evidence references, and unit/integration/live fresh-home coverage for version-aware strategy selection and strict unsupported-version failure.
