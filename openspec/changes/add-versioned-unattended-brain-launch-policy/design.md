## Context

Houmao currently handles “do not ask me for trust or permissions” inconsistently across tools and launch surfaces.

- Codex already has partial runtime-owned support through config and bootstrap code that seeds trust and suppresses approval prompts.
- Claude has only partial startup bootstrap, so fresh isolated `CLAUDE_CONFIG_DIR` homes still hit workspace trust confirmation even when the demo or runtime injects `--dangerously-skip-permissions`.
- Shared demos and ad hoc launchers compensate with tool-specific overrides, which means the same user intent is not captured once and reused everywhere.

Recent live probes on the installed tools show that the real startup surface is broader than “trust or permissions”:

- Claude Code 2.1.81 with a fresh `CLAUDE_CONFIG_DIR` and `ANTHROPIC_API_KEY` hits theme onboarding first, then custom API-key approval, then bypass-permissions confirmation, then workspace trust depending on which runtime-owned files/state are missing.
- Codex CLI 0.116.0 with a fresh `CODEX_HOME` and only `auth.json` hits trust first, and after trust/approval defaults are seeded it can still stop on a model migration prompt until runtime-owned notice/model state is updated.

Related repo-owned setup guidance in `magic-context/skills/cli-agents/*-install/` also clarifies two important boundaries:

- Claude’s host-level “skip login” setup only sets `hasCompletedOnboarding = true`, which matches one observed startup blocker but does not cover API-key approval, bypass-permissions confirmation, or workspace trust in isolated runtime homes.
- Codex’s host-level custom-provider setup explicitly treats env-only custom providers with `requires_openai_auth = false` and `wire_api = "responses"` as a first-class non-login path, so unattended runtime behavior must not assume `auth.json` is always required.

The new requirement is broader than “add one Claude flag.” Users need to say “launch this brain unattended” and let Houmao choose whatever provider-specific args, config, and runtime-state patches are necessary. That behavior is also version-dependent, so the same tool may need different launch handling on different versions.

The core constraint is timing:

```text
brain build / recipe
    -> captures launch intent
    -> writes resolved brain manifest

launch
    -> knows actual backend
    -> knows actual working_directory
    -> detects actual installed CLI version
    -> resolves compatible strategy
    -> applies version-specific actions
    -> starts provider process
```

This means build-time code cannot fully resolve unattended behavior on its own. It must persist intent, and launch-time code must resolve the concrete strategy.

## Validated Fresh-Home Findings

The current proposal is intentionally constrained by observed behavior on the installed CLIs, not by guesses:

- Claude Code 2.1.81:
  - Fresh `CLAUDE_CONFIG_DIR` with only `ANTHROPIC_API_KEY` stops at theme onboarding.
  - Adding `hasCompletedOnboarding` and trust state but omitting `customApiKeyResponses` stops at the custom API-key approval prompt.
  - Adding onboarding, trust, and API-key approval state but omitting `settings.json.skipDangerousModePermissionPrompt` stops at the bypass-permissions warning.
  - Adding onboarding, API-key approval, and dangerous-mode settings but omitting project trust stops at the workspace trust dialog.
  - A minimal working unattended seed for this version includes runtime-owned `settings.json` plus `.claude.json` fields covering onboarding, API-key approval memory, and per-project trust acceptance.
- Codex CLI 0.116.0:
  - Fresh `CODEX_HOME` with only `auth.json` stops at the trust prompt.
  - Adding `approval_policy = "never"`, `sandbox_mode = "danger-full-access"`, and `notice.hide_full_access_warning = true` still stops at trust until `[projects."<path>"].trust_level = "trusted"` is present.
  - After trust is seeded, Codex can still stop on the GPT-5.4 migration prompt.
  - Accepting that prompt writes runtime-owned state into `config.toml`, including `model = "gpt-5.4"` and `[notice.model_migrations] "gpt-5.3-codex" = "gpt-5.4"`.

These findings drive the design in two ways:

- unattended mode must cover startup operator prompts beyond classic permission dialogs
- strategies must be able to synthesize runtime-owned config/state from minimal credentials instead of requiring user-prepared tool config

## Goals / Non-Goals

**Goals:**

- Add a first-class launch policy input for “forbid startup operator prompts” instead of relying on ad hoc provider flags.
- Persist that policy from brain construction into the resolved brain manifest and runtime launch metadata.
- Resolve unattended launch behavior from the actual tool version, backend, runtime home, and working directory at launch time.
- Make unattended startup work from fresh runtime homes using only minimal credential inputs and minimal caller launch args, without depending on user-prepared per-tool no-prompt config files.
- Reuse the same strategy resolution across raw launch helpers, realm-controller headless sessions, CAO-backed launches, and demo workflows.
- Fail fast when unattended behavior cannot be guaranteed for the detected tool version.
- Support provider/version divergence without spreading `if version ...` logic across unrelated modules.

**Non-Goals:**

- Introduce silent best-effort fallback for unknown tool versions when unattended mode is requested.
- Guarantee suppression of prompts that are outside the provider/runtime-owned launch surface, such as OS-native dialogs or unrelated external systems.
- Turn user-owned tool config profiles into the sole source of truth for unattended policy behavior.
- Ship unattended registry coverage for every supported backend in the first cut; v1 explicitly covers Codex and Claude, while `gemini_headless` remains deferred and SHALL fail closed for unattended requests until a later follow-up adds versioned strategies.

## Decisions

### 1. Add an abstract launch policy input instead of more provider-specific knobs

Brain construction gains an abstract policy input such as `operator_prompt_mode`, with at least:

- default/interactive behavior
- `unattended` behavior that forbids startup operator prompts the runtime knows how to suppress

The field flow is pinned as:

- declarative recipe YAML: `launch_policy.operator_prompt_mode`
- direct build input: `BuildRequest.operator_prompt_mode: Literal["interactive", "unattended"] | None`
- resolved brain manifest: `launch_policy.operator_prompt_mode`

`None` means “use the normal interactive/default posture for this recipe/build,” not “guess a strategy.”

This intent is persisted in the resolved brain manifest as abstract policy metadata, not as pre-resolved CLI arguments or patched runtime-state payloads.

Why:

- The user intent is provider-agnostic.
- The same policy must flow through build, manifests, runtime, demos, and helper launches.
- Concrete flags/config mutations vary by tool version and backend, so storing raw injected args at build time is the wrong abstraction.

Alternatives considered:

- Provider-specific recipe fields such as `claude_skip_trust_prompt`.
  Rejected because the problem exists across tools and would multiply knobs.
- Keeping `launch_args_override` as the main interface.
  Rejected because it captures one implementation detail, not the full policy.

### 2. `unattended` covers startup operator prompts, not only permission prompts

For this change, `operator_prompt_mode = unattended` covers startup-blocking operator prompts that the runtime can suppress through provider launch args, config, or persisted runtime state.

In scope examples from current probes:

- Claude theme onboarding
- Claude custom API-key approval
- Claude bypass-permissions confirmation
- Claude workspace trust
- Codex trust
- Codex full-access acknowledgement
- Codex model migration prompts

Why:

- Real unattended failures today are caused by a mix of permission and non-permission startup surfaces.
- A narrower “permission only” contract would still produce blocked launches on the currently installed versions.

Non-goal clarification:

- This does not automatically promise that every mid-turn provider prompt can be suppressed. Mid-turn behavior remains provider-specific and may be handled in follow-up work.

### 3. Resolve the concrete unattended strategy at launch time

Launch-time code detects the actual installed tool version and resolves one compatible strategy using:

- tool
- backend
- requested `operator_prompt_mode`
- detected CLI version
- resolved working directory

The selected strategy is then applied before provider process start.

Version detection is performed against the actual launch executable with a subprocess `--version` probe such as `claude --version` or `codex --version`, followed by tool-specific parsing. Missing executables or unparseable version output are treated as explicit unattended-launch failures.

Launch-time resolution also produces a typed `LaunchPolicyProvenance` payload carried on `LaunchPlan` and persisted into session manifests. That structure records at minimum:

- requested `operator_prompt_mode`
- detected tool version
- selected strategy id
- selection source (`registry` or `env_override`)
- override env var name when an override is active

Provider-specific applied-action traces may still live in backend metadata, but this cross-backend provenance does not.

Why:

- The launch workdir is only authoritative at launch time.
- Claude workspace trust and similar state often depend on the actual launch target, not just the constructed home.
- The same brain may be launched against different installed CLI versions over time.

Alternatives considered:

- Resolve the strategy during brain build.
  Rejected because build-time code does not own the final launch context.
- Resolve once in recipes/config profiles.
  Rejected because profiles are user defaults, not version-aware runtime compatibility logic.

### 4. Strategies own runtime config/state synthesis from minimal inputs

Unattended strategies are allowed to synthesize or override runtime-owned provider config/state from minimal credential inputs. They MUST NOT require the user to pre-create tool-specific config files whose only purpose is suppressing startup prompts.

In practice this means:

- Codex unattended strategies may create or patch runtime `config.toml` from `auth.json`, `OPENAI_API_KEY`, `OPENAI_BASE_URL`, and other minimal credential inputs.
- Codex unattended strategies must also support the env-only custom-provider path when the effective provider config sets `requires_openai_auth = false` and uses the supported `responses` wire API.
- Claude unattended strategies may create or patch runtime `settings.json` and `.claude.json` from `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`, endpoint env vars, or equivalent minimal credential inputs.

Why:

- The user intent is “launch unattended with minimal help,” not “I already hand-authored the right provider config files.”
- The probes show that relying on minimal credentials alone is insufficient on both current tools.

Alternatives considered:

- Require per-tool config profiles to fully encode prompt suppression.
  Rejected because it pushes provider/version compatibility work onto the caller and breaks the “minimal help” contract.

### 5. Use a hybrid version launch policy registry

The registry is split into:

- descriptive registry entries stored as repo-owned YAML files under `src/houmao/agents/launch_policy/registry/`
- a Python resolution/apply engine
- provider-specific Python action handlers for complex mutations

The shared package lives at `src/houmao/agents/launch_policy/` so both `brain_builder.py` and `realm_controller/` can depend on it without reversing the current dependency direction.

Registry entries define:

- `schema_version`
- `tool`
- one or more `strategies`, each with:
  - `strategy_id`
  - `operator_prompt_mode`
  - `backends`
  - `version_range`
  - `minimal_inputs`
  - `evidence`
  - `owned_paths`
  - `actions`

The action engine supports generic actions such as:

- `cli_arg.ensure_present`
- `cli_arg.ensure_absent`
- `json.set`
- `toml.set`
- `validate.reject_conflicting_launch_args`
- `provider_hook.call`

Provider handlers implement complex operations such as:

- resolve trust target from working directory and git root
- materialize or patch provider runtime state idempotently
- preserve unrelated provider state while updating strategy-owned keys

`provider_hook.call` uses stable hook ids declared in registry YAML and resolved by the Python engine from a repo-owned hook table. Registry files do not import arbitrary Python symbols directly.

Each strategy’s `owned_paths` section declares the runtime-owned file paths and logical subpaths that the strategy is allowed to mutate. For example, a Claude strategy can own specific JSON paths in `.claude.json` and `settings.json`, while a Codex strategy can own specific TOML keys and project-trust sections in `config.toml`.

`launch_args_override` remains a general escape hatch for non-policy-specific launch customization, but unattended strategies own the no-prompt args they require. Exact duplicate args may be normalized away; contradictory overrides must fail validation before provider start instead of silently composing with strategy-owned behavior.

Why:

- Pure Python would scatter version logic across bootstraps and launch paths.
- Pure declarative rules would become an unsafe mini-language once trust/state mutation gets complex.
- A hybrid keeps most compatibility rules auditable in data while preserving robust code paths for complex provider semantics.
- Strategy metadata is also the right place to record whether a given behavior is documented, source-validated, live-observed, or some combination.

Alternatives considered:

- Pure Python registry tables.
  Rejected as harder to audit and easier to duplicate across call sites.
- Pure YAML/JSON DSL with no code hooks.
  Rejected because trust/state patching is too context-sensitive.

### 6. Unattended launches fail closed on unknown versions

For `operator_prompt_mode = unattended`, unknown or unsupported tool versions are treated as explicit failures by default. The system does not use parser-style floor fallback for launch policy strategies.

For controlled experiments only, the runtime may honor `HOUMAO_LAUNCH_POLICY_OVERRIDE_STRATEGY=<strategy-id>`. That override is transient, never persisted into recipes or manifests, and must be recorded noisily in `LaunchPolicyProvenance`.

Why:

- A silent fallback here would violate the user’s request and reintroduce prompt-blocked sessions.
- Prompt suppression is a safety/operability contract, not a best-effort cosmetic behavior.

The design may still allow an explicit developer override for controlled experiments, but that override is non-default and should record noisy provenance.

Alternatives considered:

- Reuse parser-style floor fallback for unknown newer versions.
  Rejected because launch policy mistakes are operationally riskier than parse drift.

### 7. Raw helpers and runtime backends share the same resolution engine

The same strategy resolution/apply layer is used by:

- generated `launch.sh` helpers
- headless backends
- CAO-backed runtime startup for both `cao_rest` and `houmao_server_rest`
- demo launch paths built on top of the same runtime/brain infrastructure

Generated `launch.sh` helpers remain shell wrappers. They invoke the shared Python launch-policy entrypoint before the final tool `exec`, mirroring the current shell-to-Python bootstrap pattern instead of replacing `launch.sh` with a Python launcher.

Runtime-managed launches route through the same shared entrypoint from `headless_base.py`, `cao_rest.py`, and the CAO-compatible `houmao_server_rest` path so that raw helpers, local headless sessions, and CAO-backed sessions cannot drift.

Why:

- This is the only way to stop the current drift between demos, raw helper launches, and runtime-managed sessions.
- The manifest-stored policy intent is otherwise undermined by different launch code paths doing different patching.

### 8. Claude runtime state moves from create-only bootstrap to idempotent strategy-managed state

Claude unattended launch requires workdir-aware trust updates, which means the old create-only `.claude.json` contract is too narrow. The new Claude strategy model may:

- create runtime state when missing
- update only strategy-owned portions when state already exists
- preserve unrelated prior/template-derived state such as unmanaged fields or MCP settings

The exact owned JSON/settings paths are declared per strategy entry, not as one global Claude-owned field list. That keeps same-tool different-version behavior explicit.

Why:

- Workspace trust depends on the launch target and may change between launches.
- We still need to preserve unrelated provider state to avoid corrupting a reused runtime home.

Alternatives considered:

- Keep create-only `.claude.json` and store trust elsewhere.
  Rejected because it does not generalize well across version-specific strategy requirements.

### 9. Current-version strategies should reflect validated minimal seeds

The initial strategy set should encode what current live probes actually required:

- Codex 0.116.x unattended startup must own trust seeding and permission/full-access defaults, it must also handle the current model migration prompt behavior, and it must preserve the env-only custom-provider path where OpenAI login is intentionally disabled.
- Claude 2.1.81 unattended startup must own dangerous-mode warning suppression, onboarding suppression, custom API-key approval memory, and per-project trust state.

Why:

- This prevents the first implementation from overfitting to partial assumptions such as “the trust entry is the only missing piece.”
- It makes the live regression matrix a first-class design input instead of a post-hoc implementation detail.

## Risks / Trade-offs

- [Registry drift as providers ship new versions] → Mitigation: fail closed for unattended mode, emit clear detected-version diagnostics, and add regression tests per strategy range.
- [Provider behavior becomes split across data rules and code hooks] → Mitigation: keep the action vocabulary narrow, keep provider handlers small, and record strategy ids in runtime metadata for debugging.
- [Official docs may not document all persisted state needed for unattended startup] → Mitigation: record evidence metadata per strategy, prefer official docs when available, and require live probes for undocumented stateful behavior.
- [Strict failure may temporarily block users after upstream auto-updates] → Mitigation: provide clear diagnostics and an explicit override path for controlled testing, but keep fail-closed as the default unattended behavior.
- [Claude state patching could overwrite unrelated user/runtime data] → Mitigation: make action ownership explicit and require idempotent merge semantics for strategy-owned keys only.
- [Different launch paths could still diverge if they bypass the engine] → Mitigation: centralize strategy resolution/apply into one shared module and require helper/runtime call sites to use it rather than open-coding patches.

## Migration Plan

1. Extend brain construction inputs, recipe parsing, and resolved brain manifests with the concrete `launch_policy.operator_prompt_mode` and `BuildRequest.operator_prompt_mode` field flow.
2. Add typed `LaunchPolicyProvenance` fields to launch-plan/session artifacts while leaving backend-specific action traces in metadata.
3. Implement the shared launch policy registry loader, selector, and action engine under `src/houmao/agents/launch_policy/`.
4. Migrate existing Codex unattended behavior into registry-backed strategies instead of leaving it as partially implicit bootstrap logic, including fresh-home trust and current model-migration prompt handling.
5. Replace Claude’s fixed create-only unattended bootstrap path with strategy-driven idempotent settings/state/trust management that works from minimal credential inputs.
6. Update generated raw launch helpers and runtime backends to invoke the shared strategy engine, including `cao_rest` and `houmao_server_rest`.
7. Add live fresh-home validation coverage and document which parts of each strategy are doc-backed vs observed.
8. Update demos, docs, and tests to request unattended mode explicitly where appropriate, cover unsupported-version failure behavior, and document the explicit Gemini deferral.

Rollback posture:

- Default interactive launches remain available.
- If unattended strategy support regresses for a provider, callers can omit the unattended policy and keep launching with prompt-allowed behavior while the registry entry is repaired.

## Resolved Scope Notes

- The controlled-experiment override surface is `HOUMAO_LAUNCH_POLICY_OVERRIDE_STRATEGY=<strategy-id>`, and it is transient rather than persisted.
- The first implementation phase ships registry-backed unattended strategies for Codex and Claude only. `gemini_headless` remains explicitly deferred and fails closed for unattended requests until a follow-up change lands.
