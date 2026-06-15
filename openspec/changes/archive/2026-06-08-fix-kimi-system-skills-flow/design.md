## Context

`add-kimi-tui-support` makes Kimi Code a maintained local-interactive provider, but the surrounding system-skill user flow still has stale assumptions. Project easy launch rejects Kimi with Gemini as headless-only. Packaged skills omit Kimi from credential and agent-definition guidance. CLI docs say managed Kimi launches pass projected skills through `--skills-dir`, while the maintained TUI launch contract should not inject a headless-only skills flag.

The local Kimi Code source reference under `extern/orphan/kimi-code` shows the underlying mismatch. Kimi discovers skills from `~/.kimi-code/skills`, `~/.agents/skills`, project `.kimi-code/skills`, and project `.agents/skills`; it does not automatically discover `<KIMI_CODE_HOME>/skills`. Kimi prompt mode supports `--skills-dir`, but that flag replaces auto-discovered directories and belongs to the headless prompt-mode path. Kimi also supports additive `extra_skill_dirs` in `config.toml`, which preserves normal user and project discovery while adding Houmao-managed projected skill paths.

## Goals

- Let project-backed Kimi specialists and profiles use the maintained TUI/local-interactive launch path when the operator does not request `--headless`.
- Keep Gemini as the project easy launch surface's required-headless exception.
- Make Houmao-managed Kimi system skills reachable from managed Kimi homes without injecting TUI `--skills-dir`.
- Align packaged `houmao-credential-mgr`, `houmao-agent-definition`, and touring guidance with Kimi as a supported tool.
- Repair credential reference links and add Kimi credential reference material used by installed skills.
- Correct docs so `KIMI_CODE_HOME`, project `.kimi-code/skills`, headless `--skills-dir`, and managed TUI skill reachability are described consistently.

## Non-Goals

- Do not add a Kimi browser-login helper unless a maintained CLI/login import path exists.
- Do not change Kimi Code itself or assume new upstream discovery behavior outside the local source reference.
- Do not preserve the stale project easy Kimi headless-only restriction for compatibility.
- Do not replace all provider documentation. Scope updates to Kimi-relevant system-skill and launch surfaces.

## Decisions

### Kimi Project Launch Posture

`houmao-mgr project agents launch` will allow Kimi specialists and Kimi-backed project profiles to launch without `--headless`. The command will delegate through the same native managed-agent launch path used by other TUI-capable providers, with launch posture resolving to local interactive when headless posture is omitted. The Gemini rejection remains unchanged and continues to explain that Gemini project easy launches require `--headless`.

### Managed Kimi Skill Discovery

Brain construction will continue projecting selected private skills and Houmao-owned system skills into the Kimi runtime home according to the Kimi adapter's `skills_projection.destination`, currently `<runtime-home>/skills`. For managed Kimi homes, when that projected skill root exists or managed system skills are selected, construction or launch preparation will ensure the effective Kimi `config.toml` includes that absolute projected skill root in `extra_skill_dirs`.

The implementation should use existing TOML helpers where possible so it preserves unrelated user-authored Kimi config, avoids duplicate `extra_skill_dirs` entries, and rewrites only the affected key. This path is additive and keeps Kimi's native discovery roots active.

The maintained TUI/local-interactive Kimi path will not inject `--skills-dir`. The Kimi headless prompt-mode strategy may continue to own final `--skills-dir` behavior for headless `kimi_headless`, where that flag is intentionally part of the prompt-mode command contract.

### Manual Kimi System-Skills Installation

`houmao-mgr system-skills install --tool kimi` remains a projection command. When `--home` is omitted and no `KIMI_CODE_HOME` is set, the project default `<cwd>/.kimi-code` produces projected skills under `<cwd>/.kimi-code/skills`, which is a real Kimi project discovery root when Kimi runs from that project. Explicit `--home` or `KIMI_CODE_HOME` targets are still useful for status, uninstall, and file placement, but docs and plain output must not claim arbitrary `<KIMI_CODE_HOME>/skills` paths are auto-discovered by Kimi.

### Packaged Credential Skill Scope

`houmao-credential-mgr` will include Kimi in credential CRUD guidance for project and direct native-agent credential roots. Add/set reference material will document Kimi-supported credential inputs such as API key, base URL, provider type, model name, code base URL, OAuth host variants, telemetry disablement, `config.toml`, and credential JSON inputs according to the current CLI surface.

Login-helper guidance remains limited to providers with maintained login helpers. Kimi CRUD support must not imply a Kimi login helper exists.

### Packaged Agent-Definition Guidance

`houmao-agent-definition` will present Kimi as a supported specialist/profile tool. Kimi examples must use `tool: kimi` or `--tool kimi` when the selected provider is Kimi, and Kimi launch examples must omit `--headless` unless the user asked for headless. The skill should keep the existing "prefer TUI/local interactive when supported" rule and update the required-headless exception to Gemini only.

Credential reference links used by `houmao-agent-definition` will be made resolvable. The implementation may add local reference pages under that skill or repoint references at the existing credential-manager references, but installed skill content must not contain broken relative links.

## Risks and Tradeoffs

Writing `config.toml` creates a merge risk. The implementation should reuse the repo's TOML state helpers and add focused tests that preserve unrelated keys, append only the managed skill root, and avoid duplicates.

Absolute `extra_skill_dirs` entries are runtime-local. That is acceptable for Houmao-managed homes because build and launch preparation regenerate the runtime home contract; docs should not present those paths as portable project config.

Kimi source behavior may drift. Tests should encode the current local-source-backed contract and docs should phrase discovery as current Kimi Code behavior, not a universal Agent Skills rule.

Packaged skill edits can become broad. Keep this change to Kimi support, credential reference repair, and stale headless-only language.

## Migration Plan

No compatibility shim is needed for the previous Kimi headless-only project easy behavior. Existing Kimi specialists can launch through TUI once the command gate is removed.

For reused managed Kimi homes, the next managed build or launch preparation should rewrite the effective Kimi config to include the managed projected skill root. Existing unrelated Kimi config values should remain intact.

Manual external Kimi installs remain on disk where they were projected. Operators who installed into arbitrary `KIMI_CODE_HOME` values may need to either run Kimi from a project whose `.kimi-code/skills` contains those projections or add the projected root to Kimi `extra_skill_dirs`; docs will make that boundary explicit.

## Open Questions

- Should managed Kimi `extra_skill_dirs` be written during brain construction only, or also rechecked during launch preparation for reused homes? The safer implementation is to do both if construction and launch can be entered independently.
- Should plain `system-skills status --tool kimi` warn when the resolved projection root is not one of Kimi's native discovery roots? The spec requires the output to avoid false discovery claims; a warning is optional unless implementation proves it is useful.
