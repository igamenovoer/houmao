## Context

See [proposal.md](proposal.md) for motivation. The current Houmao path models Kimi as lacking a native system-prompt surface, selects `auto_skill_system_prompt`, projects `houmao-auto-system-prompt`, and exposes `houmao-mgr agents self system-prompt show` so the skill can retrieve the composed prompt. Projection does not prove that Kimi invoked the skill before substantive work.

The local Kimi source checkout is the primary provider reference. In Kimi Code 0.34, `packages/agent-core-v2/src/workspace/workspaceAgentProfileLoader/internal/systemFile.ts` loads `$KIMI_CODE_HOME/SYSTEM.md` as the default main-agent prompt override. `packages/agent-core-v2/src/app/agentProfileCatalog/profile-shared.ts` makes `${base_prompt}` embed the built-in default prompt, and `packages/agent-core-v2/src/_base/utils/render-prompt.ts` performs one substitution pass over recognized `${name}` variables. Project or explicit main-agent definitions can take precedence over `SYSTEM.md`. The v2 engine is the default in 0.34, while `KIMI_CODE_LEGACY_FLAG=1` selects the old engine.

The implementation must not target the interface proposed in GitHub PR 523. That pull request closed without merge, and current Kimi 0.34 has no `--agents-dir` option. Current native choices are `SYSTEM.md` and Markdown `--agent-file`; only `SYSTEM.md` applies uniformly to fresh headless, fresh TUI, and provider-native resume without adding creation-only selector arguments.

## Goals / Non-Goals

**Goals:**

- Give maintained Kimi launches the same deterministic pre-first-turn role contract as other native prompt providers.
- Project the complete composed Houmao launch prompt while retaining Kimi's built-in environment, skill, workspace-instruction, and plugin sections.
- Make provider version, engine, prompt-file ownership, precedence, and provenance explicit and testable.
- Delete the managed auto-skill architecture and its public prompt-retrieval CLI instead of preserving a dormant fallback.
- Establish 0.34.x as the baseline qualification evidence while supporting every Kimi release at or above 0.34.0.

**Non-Goals:**

- Supporting Kimi releases before 0.34.0.
- Migrating or resuming sessions created under the auto-skill role-injection contract.
- Retrofitting a role prompt into an already-running TUI adopted through `agents self join`; the native guarantee begins at the next Houmao-owned provider start.
- Replacing Kimi's built-in prompt, tool policy, skills, `AGENTS.md` handling, or plugin instruction assembly.
- Making deprecated CAO backends a maintained Kimi runtime surface.

## Decisions

### 1. Set a Kimi 0.34.0 floor with no upper limit and force agent-core-v2

Replace both Kimi strategy ids with minimum-version strategies and set `supported_versions` to `>=0.34.0`. Strategy evidence will point to current 0.34 source paths and fresh live probes, but strategy selection will apply the same native contract to every later Kimi version. Version selection fails closed only for versions below 0.34.0 or versions that cannot be parsed.

Every managed Kimi process environment will set `KIMI_CODE_LEGACY_FLAG=0` as a strategy-owned value after auth-bundle, profile, and inherited environment resolution. The launch path will reject any later attempt to replace it with a truthy legacy value. This applies to headless turns, local-interactive startup, and relaunch.

Alternative considered: cap support at the latest qualified minor release. Rejected because Kimi support is intentionally a minimum-version contract; new releases remain supported unless a concrete incompatibility requires a future breaking floor change.

### 2. Add a native managed-home role-injection method

Add `native_home_system_prompt` to `RoleInjectionMethod` and remove `auto_skill_system_prompt`. For Kimi headless and Kimi local-interactive provider starts, the qualified strategy selects this method. `RoleInjectionPlan.prompt` will be documented and tested as the complete effective launch prompt already composed from the role, overlays, managed header, identity, memory, and other launch-owned sections, not merely the raw role file.

The managed `SYSTEM.md` bytes will be:

```text
${base_prompt}

<complete effective Houmao launch prompt>
```

The file is plain Markdown with no frontmatter. The `${base_prompt}` reference keeps Kimi's built-in default prompt and its dynamic sections. Houmao will neither duplicate `${skills}`, `${agents_md}`, `${plugin_sections}`, nor reconstruct Kimi's provider-owned prompt in Python.

Kimi 0.34 recognizes `${skills}`, `${skills_section}`, `${agents_md}`, `${cwd}`, `${cwd_listing}`, `${os}`, `${shell}`, `${now}`, `${additional_dirs_info}`, `${base_prompt}`, and `${plugin_sections}` in user prompt templates. Its renderer has no literal escape syntax for recognized placeholders, and a later Kimi release may assign meaning to a previously unknown name. Before writing the file, Houmao will therefore reject every `${identifier}` token in the effective Houmao prompt and report the token and source prompt. Bare dollar signs and text that does not match Kimi's placeholder grammar remain unchanged. The launch-owned leading `${base_prompt}` is added only after this validation.

Alternative considered: use `--agent-file`. That option binds an explicit custom agent only when creating a session, conflicts with `--continue` and `--session`, and has higher precedence than `SYSTEM.md`. It would require separate fresh and resume contracts. Alternative considered: escape dollar signs. Kimi's one-pass regular-expression renderer does not define an escape sequence, so dollar doubling still leaves a recognized `${name}` match.

### 3. Give projection one shared implementation and two enforcement points

Create a Kimi prompt projection helper owned by the agents runtime. It will validate prompt variables, render canonical file bytes, write by atomic replacement with restrictive permissions, remove an empty managed projection, compute hashes, and validate higher-priority agent sources. Brain construction and provider-start planning will both call the helper for different reasons:

- Brain construction runs it after setup and auth projection so `SYSTEM.md` is a final runtime-owned path. It records construction provenance beside the stored effective prompt.
- Provider-start planning runs it before every fresh start or relaunch, using the `RoleInjectionPlan.prompt`. It repairs drift by atomically restoring the canonical bytes, rechecks precedence conflicts, and records launch verification in `LaunchPlan.metadata` and the session manifest.

The shared helper makes the byte format and diagnostics single-sourced. Rechecking at provider start closes the interval between build and execution and covers relaunch. A promptless Kimi build removes `SYSTEM.md`; it does not leave a file copied from an earlier setup or retained home.

Provenance will include the injection method, `SYSTEM.md` relative path, effective-prompt SHA-256, projected-file SHA-256, built-in-prompt preservation flag, engine requirement, validation result, and projection state. It will not claim to know the final rendered Kimi prompt because Kimi fills dynamic variables at session creation.

Alternative considered: write only during brain construction. That misses low-level brain builds whose effective role is resolved later and cannot detect drift before relaunch. Alternative considered: write only during launch planning. That omits build-time ownership and leaves the constructed home inconsistent with its stored effective prompt until startup.

### 4. Reject native-prompt bypasses rather than guessing precedence

Before Kimi starts, validation will reject `--agent` and `--agent-file` in launch arguments, including `--name=value` forms. It will inspect Kimi project agent roots and configured extra agent directories for an `agent` profile with `override: true`, using the same frontmatter name fallback needed to identify Kimi's default main agent. Project files are never deleted or rewritten.

User-home and plugin agent definitions that remain below the managed `SYSTEM.md` precedence do not fail validation. A pre-change resumed session is unsupported because its bound agent and recorded role method were created outside this contract; old session manifests containing `auto_skill_system_prompt` will no longer validate as current manifests.

Alternative considered: silently strip explicit agent args or edit project agent files. Both would hide caller intent and mutate user-owned project state. A clear pre-start error preserves the authority boundary.

### 5. Replace bootstrap booleans with an explicit native prompt contract

Rename the launch-policy `system_prompt_bootstrap` model to a native `system_prompt` contract. Remove `provider_skills` and `startup_visible_skill_metadata` from prompt selection; provider skill support remains part of tool adapter and skill-projection behavior, not a role-injection fallback.

The registry contract will distinguish backend-native methods used by Claude/Codex from Kimi's managed-home method. Kimi metadata will declare `SYSTEM.md`, the v2 requirement, precedence validation, and current evidence. The resolver selects one native method or returns an incompatibility; it never selects a skill or ordinary chat fallback for a non-empty effective prompt.

The Kimi registry actions retain headless argument canonicalization, TUI native `--auto`, and automatic permission config. They add native-prompt and engine validation without combining credential readiness, permission mode, and role injection into one boolean.

Alternative considered: set the current `native_system_prompt` boolean to true and special-case Kimi in `_native_role_injection_method()`. That would work mechanically but would leave the skill-fallback fields, omit owned-path and precedence semantics, and keep the model too weak to diagnose why a nominally native surface is bypassed.

### 6. Delete the auto-skill and self-prompt surfaces completely

Delete the packaged auto-skill asset and `auto_skills.py`. Remove `BuildRequest.required_auto_skill_names`, auto-skill collision checks, provider discovery mutation, construction provenance, launch-plan projection, the `auto_skill_system_prompt` enum values, and the public `agents self system-prompt show` Click group and helper.

Remove `auto_skill_name` from the system-skill manifest model and source manifest. Bump that source schema to `houmao-system-skills.v5` because the required top-level shape changes. The static admin/agent packs, installed `houmao-skill-config.v1`, and their ownership semantics do not change.

Existing session-manifest schema versions will remove the retired role-injection enum value without a compatibility parser. This deliberately makes manifests that depend on the old method fail current validation while leaving unrelated current manifests structurally unchanged.

Alternative considered: retain the skill package and CLI as deprecated. There is no maintained consumer after native Kimi projection, and retaining them would preserve two apparent sources of truth for the same prompt.

### 7. Update the legacy Kimi compatibility adapter only to valid 0.34 syntax

The deprecated CAO compatibility path continues to receive a `cao_profile`, not a managed brain home. Its Kimi adapter will replace the obsolete YAML `agent.yaml` payload with a Kimi 0.34 Markdown agent file, preserve the built-in prompt with `${base_prompt}`, apply the same all-placeholder validation, and use a 0.34-valid permission flag. This prevents an immediate syntax break without claiming that CAO uses the maintained `SYSTEM.md` lifecycle or supports resume.

Alternative considered: manufacture a temporary `KIMI_CODE_HOME` for CAO. That would require copying or rebinding ambient credentials and config into a second home, which materially expands a deprecated backend.

### 8. Requalify Kimi behavior and documentation as one versioned unit

Unit tests will cover canonical file bytes, all placeholder-shaped tokens, empty/stale handling, atomic repair, provenance, precedence conflicts, the minimum-only version range, v2 env ownership, manifest/schema removal, CLI removal, and 0.34 Markdown compatibility profiles. Integration tests will exercise both `kimi_headless` and unattended Kimi TUI with the standard Kimi fixture credentials.

The maintained TUI signal profile and recorded corpus will use 0.34.x as baseline evidence, while the Kimi profile selector applies it to every version at or above 0.34.0. Pre-0.34 profiles will be removed from supported selection; old recordings may remain only when clearly marked historical and excluded from qualification. README, getting-started, build/run references, CLI reference, developer behavior-testing resources, and system-skill docs will remove every active auto-skill instruction and state the breaking minimum-version boundary.

## Risks / Trade-offs

- [A later Kimi release adds a prompt variable] → Reject every `${identifier}` occurrence in Houmao-authored prompt text, not only the variables known in 0.34, so new provider variables cannot silently reinterpret an existing role.
- [A role legitimately needs to show `${cwd}` as literal text] → Fail with a precise diagnostic and require the role author to rephrase the example; Kimi 0.34 provides no escape contract that preserves those bytes.
- [A project main-agent override unexpectedly bypasses `SYSTEM.md`] → Parse and reject the exact higher-priority default-agent override before process start, and cover project plus extra-agent roots in tests.
- [The managed file changes between validation and Kimi reading it] → Use atomic replacement, restrictive permissions, provider-state locking, and immediate pre-exec hash verification. The managed home is an operational boundary, not a defense against a hostile same-user process.
- [`${base_prompt}` changes Kimi behavior across releases] → Treat this as intended provider ownership; Houmao tests for the required Houmao suffix and Kimi dynamic sections rather than snapshotting Kimi's whole built-in prompt, and fixes concrete incompatibilities without preemptively capping versions.
- [Removing old manifest enum values blocks an operator's existing session] → Surface an explicit rebuild/start-fresh diagnostic. This is the declared breaking boundary, not a format to migrate silently.
- [Re-recording the 0.34 TUI corpus reveals detector drift] → Keep the profile unmaintained until high-rate labeled recordings and sparse replay pass; do not relabel 0.23 evidence as 0.34 evidence.

## Migration Plan

1. Land the model, registry, projection, schema, CLI-removal, adapter, test, and documentation changes together so no release exposes both role-delivery methods.
2. Require Kimi Code 0.34.0 or later and run baseline source plus live qualification on 0.34.x for headless, fresh TUI, resumed TUI, prompt precedence, and template-variable behavior.
3. Rebuild Kimi brains with the clean-home mode. Do not reuse homes containing `skills/houmao-auto-system-prompt` or session manifests whose role method is `auto_skill_system_prompt`.
4. Stop old managed Kimi sessions and start new sessions from the rebuilt brains. Existing provider history may be exported separately, but Houmao does not resume it under the new contract.
5. Publish the breaking version floor and removed CLI/skill surfaces in README and reference docs.

Rollback is release-level only: restore the prior Houmao release together with homes and sessions created by that release. Mixing the new code with old auto-skill manifests, or the old code with new native-prompt manifests, is unsupported.
