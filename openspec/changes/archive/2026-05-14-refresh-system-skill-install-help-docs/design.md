## Context

The project now has two parallel system-skill installation stories:

- external Skills CLI installation through `npx skills add https://github.com/igamenovoer/houmao/tree/main/src/houmao/agents/assets/system_skills/`, which is the preferred path when `npx` and internet access are available because it lets users choose from the GitHub main-branch system-skill collection;
- Houmao's own `houmao-mgr system-skills install`, which remains the supported package-local path for offline installs, project-local homes, explicit homes, named sets, subset selection, symlink/copy projection, and cleanup of retired skill projections.

The project also added skill-level help to every current packaged system skill. That help is prompt-level behavior inside installed skills, not a `houmao-mgr system-skills help` CLI subcommand.

README has started to reflect these decisions, but the docs site and main OpenSpec docs specs still contain older assumptions, especially the idea that `houmao-mgr system-skills install` is always the first onboarding step.

## Goals / Non-Goals

**Goals:**

- Normalize the system-skill installation story across README, docs index, system-skills overview, and system-skills CLI reference.
- Make `npx skills add <GitHub main system_skills dir>` the recommended route only when `npx` and internet access are available.
- Keep `houmao-mgr system-skills install` first-class for offline, installed-package, explicit-home, named-set, subset-skill, symlink/copy, and cleanup workflows.
- Document skill-level help as explicit read-only prompt behavior available after installation.
- Update OpenSpec docs contracts so current docs do not conflict with the specs.
- Add focused docs guard tests for these claims.

**Non-Goals:**

- Do not add or change any `houmao-mgr` command.
- Do not change the packaged system-skill catalog or install behavior.
- Do not add generated help content or derive help from the CLI.
- Do not broaden this pass into a full rewrite of loop authoring, mailbox, gateway, or skill asset docs.
- Do not archive completed OpenSpec changes as part of this docs refresh.

## Decisions

### 1. Document two installation paths by environment fit

The docs should not frame one installer as universally replacing the other. Instead, they should present a decision:

```text
has npx + internet?
  yes -> npx skills add <GitHub main system_skills dir>
  no  -> houmao-mgr system-skills install

needs named sets, subset skills, explicit homes, symlink/copy, cleanup?
  yes -> houmao-mgr system-skills install
```

This keeps the README's recommended quick path intact while preserving the CLI reference as the authoritative source for Houmao-managed projection semantics.

### 2. Keep CLI reference focused on `houmao-mgr`

`docs/reference/cli/system-skills.md` should mention the `npx` path as adjacent installation guidance, but it should not become documentation for the external Skills CLI. The page's main body remains the `houmao-mgr system-skills` command reference.

### 3. Treat skill help as prompt-level behavior

Docs should explicitly say that `$houmao-touring help` and similar prompts are answered by the installed skill's top-level `SKILL.md`. They are read-only usage responses and not a new `houmao-mgr system-skills help` command.

This distinction matters because the user may install skills through `npx` without a local Houmao CLI yet, while CLI-oriented readers may otherwise search for a nonexistent subcommand.

### 4. Align specs with current README structure

The old `readme-structure` requirement that made system-skill installation part of step 0 should be removed or superseded. Step 0 is installation and prerequisites for Houmao itself; step 1 is the recommended agent-driven path, including system-skill installation choices and skill-level help.

## Risks / Trade-offs

- [Duplicated install guidance drifts between README, docs index, overview, and CLI reference] -> Keep the wording compact and add guard tests for the key phrases rather than checking long prose.
- [Readers confuse `npx skills add` with Houmao-managed projection semantics] -> State that `houmao-mgr system-skills install` owns named sets, subset selection, explicit homes, symlink/copy, and cleanup behavior.
- [Readers look for `houmao-mgr system-skills help`] -> State that help is prompt-level installed-skill behavior, not a CLI subcommand.
- [Docs over-recommend internet-dependent installation] -> Qualify `npx` as recommended only when `npx` and internet access are available.

## Migration Plan

1. Update delta specs for README structure, README system-skill guidance, docs index, system-skills overview, and CLI reference.
2. Update affected docs in the implementation phase.
3. Add docs tests that check the docs index, overview, CLI reference, and README for the normalized install/help story.
4. Run focused docs tests and `openspec validate refresh-system-skill-install-help-docs --strict`.

Rollback is just reverting docs and spec changes. No runtime state or package migration is involved.

## Open Questions

- Should the docs reference the external Skills CLI by name only, or should they include any troubleshooting guidance for environments without `npx`? The default design keeps troubleshooting out of scope and points such users to `houmao-mgr system-skills install`.
