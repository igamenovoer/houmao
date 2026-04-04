## Context

Houmao-launched agent startup currently spans three different concerns that Houmao does not model cleanly:

- setup projection copies tool-owned baseline files such as `config.toml`, `settings.json`, or other provider state into the runtime home,
- unattended launch policy mutates runtime-owned startup state to suppress trust, approval, and migration prompts, and
- credential readiness determines whether the selected provider can authenticate once startup reaches a ready state.

Today these concerns are blurred. The launch-policy metadata and validation code still describe unattended compatibility partly in terms of auth material, while the actual startup-suppression behavior for current tools is driven by runtime config/state and interactive CLI flags. The concrete failure surfaced on Codex, but the contract gap is Houmao-wide: unattended launch should work the same way for TUI and headless launches, for Claude Code and Codex today, and for future tools added to the registry. Separately, `project easy specialist create` hardcodes setup selection to `default`, which drops real setup semantics whenever a tool needs a non-default setup.

The result is the wrong abstraction boundary: Houmao risks treating auth state as the way to make unattended launch work, when the real contract is that unattended startup owns specific runtime config/state and launch surfaces while provider setup and credentials remain distinct inputs.

## Goals / Non-Goals

**Goals:**

- Define unattended launch as a runtime-owned contract over provider-home config keys and launch-arg surfaces.
- Make runtime-home construction explicitly two-phase: copy selected setup baseline first, then apply unattended overrides onto the runtime copy.
- Separate unattended compatibility checks from credential-readiness checks.
- Preserve explicit setup selection through `project easy specialist create`, generated presets, and stored specialist metadata.
- Make unattended-owned startup surfaces authoritative over conflicting copied setup values and caller launch inputs.

**Non-Goals:**

- Do not automate tool login flows or synthesize fake auth state to avoid prompts.
- Do not infer a setup from a credential bundle name or API endpoint.
- Do not redesign provider selection beyond preserving and projecting the selected setup correctly.
- Do not change as-is launch behavior for operators who intentionally opt out of unattended startup.

## Decisions

### Decision: Split the contract into setup baseline, unattended override, and credential readiness for every launched tool

Houmao will model three separate layers for every Houmao-launched tool:

- setup baseline: copied from the selected tool setup bundle into the runtime home,
- unattended override: runtime-owned mutations that force no-prompt startup semantics for supported versions,
- credential readiness: validation that the resolved provider has the secret material it needs.

Rationale:

- This matches the current tool families: Claude and Codex both suppress unattended startup prompts through a combination of runtime state and launch surfaces rather than through secret material alone.
- It gives future tools one consistent contract: setup supplies the baseline, unattended owns the startup overrides, and credentials satisfy readiness.
- It prevents implementation shortcuts that conflate login state with startup-prompt suppression.

Alternatives considered:

- Keep treating auth material as part of unattended compatibility. Rejected because it misstates the actual startup contract and encourages provider-specific hacks.
- Infer provider/setup from auth bundle contents. Rejected because credentials and setup are orthogonal inputs.

### Decision: Runtime-owned unattended state overrides copied setup values in the runtime home

For unattended launch, Houmao will treat declared strategy-owned runtime-home keys as authoritative at provider start. The selected setup baseline is still copied first, but strategy-owned keys are overwritten in the runtime copy before launch.

Examples for current tools:

- Codex: `config.toml` keys such as `approval_policy`, `sandbox_mode`, trust, and migration state
- Claude: runtime JSON state such as onboarding, dangerous-mode suppression, and project trust markers

Rationale:

- The operator asked for unattended launch semantics, so runtime-owned no-prompt behavior must win over baseline setup defaults on those keys.
- This keeps provider-specific setup content intact while making no-prompt startup deterministic.

Alternatives considered:

- Preserve copied setup values when they conflict with unattended values. Rejected because it makes unattended behavior dependent on arbitrary setup content.
- Prefer only CLI flags or only config mutation for every tool. Rejected because different tools expose different startup-suppression surfaces, and the contract needs to be generic across current and future tools.

### Decision: Unattended-owned launch surfaces override conflicting caller launch inputs for every tool

When `operator_prompt_mode = unattended`, Houmao will treat the effective startup launch surface as runtime-owned. Caller launch overrides that attempt to set contradictory startup behavior for a strategy-owned unattended surface will be removed, replaced, or otherwise canonicalized so the final effective launch behavior remains unattended.

For current tools this includes direct no-prompt flags and config-override syntax where the tool supports it. Future tools added to the unattended registry will follow the same rule through their declared strategy-owned surfaces.

Rationale:

- The operator asked for unattended launch semantics, so Houmao should make the launch unattended instead of depending on the user to know or supply the right low-level flags.
- The launch-policy registry already declares owned paths and action order; extending that ownership to equivalent launch-override surfaces keeps the contract coherent.
- Canonicalizing the effective launch surface keeps unattended behavior deterministic even when baseline config or caller launch inputs disagree.

Alternatives considered:

- Reject conflicting overrides and fail launch. Rejected because the user asked for unattended launch to be achieved authoritatively rather than delegated back to the caller's low-level launch choices.
- Allow launch args to win over unattended strategy. Rejected because it defeats the point of runtime-owned unattended behavior.

### Decision: Project-easy must persist setup explicitly and never infer it from credentials

`houmao-mgr project easy specialist create` will accept an explicit `--setup` selection with a default of `default`, validate that the setup exists for the selected tool, and persist that setup into the project catalog plus generated preset projection for any tool that supports setup bundles.

Rationale:

- Setups can carry real startup semantics for any supported tool, not just Codex.
- Preserving explicit setup avoids hidden credential-to-provider inference rules.

Alternatives considered:

- Continue hardcoding `default` for easy specialists. Rejected because it discards operator intent and breaks non-default tool setups.
- Infer non-default setup from credential names such as `yunwu-openai`. Rejected because it is heuristic and unstable.

## Risks / Trade-offs

- [Existing easy specialists already persisted with `default`] → Leave existing records unchanged and document that operators must update or recreate specialists if they want a non-default setup; do not silently remap old specialists from credentials.
- [Operator-supplied launch args may not match the final unattended-effective args] → Persist diagnostics/provenance that show which startup surfaces were runtime-owned and therefore canonicalized by Houmao.
- [Tool-specific bootstrap helpers may diverge from the shared contract] → Align those helpers with the launch-policy contract or narrow them to non-policy-preserving utilities so the runtime has one authoritative unattended mutation model.
- [Future tool versions may move startup prompts to new config or flag surfaces] → Keep the versioned registry as the place where owned paths, evidence, and ordered actions are updated per supported version range.

## Migration Plan

- Update the launch-policy spec and runtime implementation so unattended strategies describe runtime-owned config/state and launch surfaces rather than credential forms.
- Update the project-easy CLI contract and implementation to persist explicit setup selection.
- Keep existing specialist records unchanged on disk; no automatic data migration will infer a new setup from old credentials.
- Add focused tests for:
  - runtime-home baseline copy plus unattended override ordering,
  - canonicalization of conflicting launch inputs for current unattended tools,
  - project-easy non-default setup persistence.

## Open Questions

- Whether tool-specific config-override canonicalization should be implemented by a generic launch-policy parser for config-override args or by per-tool provider hooks that interpret those args.
- Whether existing tool-specific bootstrap helpers should be reduced to pure file-format utilities once the launch-policy engine becomes the sole owner of unattended mutation semantics.
