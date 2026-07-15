## Context

`houmao-mgr system-skills` currently treats the `--tool` selector as both a tool identifier and an installation profile. The shared installer maps each selector to a home-relative skill destination; the CLI separately resolves the effective home. Current selectors include `kimi`, and local Kimi Code source and docs show that Kimi Code scans both Kimi-specific skill roots and generic `.agents/skills` roots.

The requested behavior adds a non-tool installation target, `universal`, for the cross-client Agent Skills convention at `~/.agents/skills`. The same change should clarify that the existing `kimi` selector means Kimi Code CLI. It should not add `kimi-code` as a selector. The legacy MoonshotAI `kimi-cli` repository says Kimi CLI is evolving into Kimi Code CLI and that the legacy project will be gradually wound down, so Houmao help text should warn users about that naming boundary.

## Goals / Non-Goals

**Goals:**
- Add explicit `system-skills` install/status/uninstall support for `universal`, resolving by default to `~/.agents/skills`.
- Keep `kimi` as the only Kimi selector and define it as Kimi Code CLI.
- Correct operator-facing Kimi discovery wording for `$KIMI_CODE_HOME/skills`.
- Preserve the existing selected-skill projection, retired cleanup, status, uninstall, copy, and symlink behaviors.

**Non-Goals:**
- Add a `kimi-code` alias.
- Add support for the legacy MoonshotAI `kimi-cli` project as a separate target.
- Change managed launch or managed join to install into `~/.agents/skills`.
- Add an environment variable such as `AGENTS_HOME`; the universal default is the real OS home `.agents` directory unless the operator passes `--home`.
- Generalize `system-skills` into a full arbitrary Agent Skills package manager.

## Decisions

1. Treat `universal` as an installation target, not a runtime tool.

   The public flag remains `--tool` for compatibility with the existing command shape, but docs and help can describe the accepted values as supported targets. `universal` resolves to a home root of `~/.agents` by default and uses the existing destination root `skills/`, which produces `~/.agents/skills/<houmao-skill>/`.

   Alternative considered: make `--tool universal` point directly at `~/.agents/skills` with an empty destination root. That would diverge from the existing home-plus-destination model and make `--home` semantics inconsistent. Keeping `--home` as the root that contains `skills/` matches every other selector.

2. Keep the shared installer surface mostly unchanged.

   The low-level functions can keep their current `tool` parameter names during this change, while their supported selector map gains `universal`. CLI validation should stop using the home-env-var map as the source of truth because `universal` intentionally has no env var. A small target-profile resolver or separate supported-target set is enough.

   Alternative considered: rename all internal `tool` terms to `target`. That is clearer long term, but it would touch managed launch, mailbox, and auto-skill call sites that do not need behavior changes.

3. Do not add `kimi-code` as an alias.

   Existing Houmao runtime, credential, and process-detection code uses canonical tool name `kimi` for Kimi Code. The selector should stay `kimi` and the help text should define it precisely. If an operator enters `kimi-code`, the command should reject it and point them to `kimi`.

   Alternative considered: accept `kimi-code` as a convenience alias. The user explicitly rejected that shape, and it would create a second spelling for a single existing tool family.

4. Replace the stale Kimi discovery caveat with accurate wording.

   Current CLI/docs wording says Kimi Code does not automatically discover arbitrary `$KIMI_CODE_HOME/skills`. Kimi Code does scan `$KIMI_CODE_HOME/skills` when launched with that Kimi Code home. The more precise statement is that `system-skills --home <path>` only places files, and Kimi Code sees them when that same path is its active `KIMI_CODE_HOME`, when the path is passed through `--skills-dir`, or when it is configured in `extra_skill_dirs`.

   Alternative considered: remove the Kimi note entirely. Keeping a concise note is useful because explicit `--home` can still be misunderstood as reconfiguring a future Kimi launch.

## Risks / Trade-offs

- `universal` is not a real tool while the CLI option is still named `--tool` -> Mitigate through help/docs wording that calls values supported targets and explains `universal`.
- Defaulting to `~/.agents` could surprise tests or scripts that expect project-scoped homes -> Mitigate with explicit tests that patch HOME and assert omitted-home universal resolution uses the user home, not the current working directory.
- Operators may pass `--home ~/.agents/skills` and get `~/.agents/skills/skills` -> Mitigate with docs and plain output that show `--home` is the universal home root and the skill root is `<home>/skills`.
- Some clients may ignore parts of Houmao skill metadata that Codex understands -> Mitigate by describing `universal` as file projection for clients that scan Agent Skills, not as a guarantee that every client supports every optional field.
