# Update Project-Local Agent Skills

## Workflow

1. **Resolve the checkout and project homes**. Use the explicit checkout or current repository root. Select user-named project homes, or every existing home from **Target Mapping** when the user names none.
2. **Select system-skill packs** per target. Preserve packs from a current config unless the user explicitly changes them; use `admin` for a clean new project home. See **Pack and Projection Policy**.
3. **Capture preflight state**. Run current-source status with an explicit home, list the target skill root, and record every Houmao system-skill and development-skill entry with its file type or symlink target.
4. **Classify lifecycle ownership** using **Current Config and Legacy Receipt Handling**. Stop for approval when current config ownership is absent but selected destinations already exist.
5. **Refresh packaged system skills** with `pixi run houmao-mgr system-skills upgrade` for current configs or `install` for clean targets. Pass one tool, its explicit project home, every selected pack, and `--symlink`.
6. **Preserve and refresh development skills** using **Development Skill Policy**. Add or remove a development skill only when the user explicitly requests that change.
7. **Verify every selected home** using **Verification Contract**, then report preserved, refreshed, added, removed, blocked, or conflicting entries.

If a request does not map cleanly to these steps, use the native planning tool to build and execute a bounded plan from the selected homes, packs, projection mode, and named development skills.

## Target Mapping

Always pass the absolute project-home path through `--home`. This prevents `CLAUDE_CONFIG_DIR`, `CODEX_HOME`, `KIMI_CODE_HOME`, or `COPILOT_HOME` from redirecting a project-local update.

| Project-local agent home | CLI tool | Skill root |
| --- | --- | --- |
| `<checkout>/.agents` | `universal` | `<checkout>/.agents/skills` |
| `<checkout>/.claude` | `claude` | `<checkout>/.claude/skills` |
| `<checkout>/.codex` | `codex` | `<checkout>/.codex/skills` |
| `<checkout>/.kimi-code` | `kimi` | `<checkout>/.kimi-code/skills` |
| `<checkout>/.github` | `copilot` | `<checkout>/.github/skills` |

Do not create an absent project home unless the user names it or asks for every supported home.

## Pack and Projection Policy

Use symlinks by default for development. A symlinked packaged root tracks edits under `src/houmao/agents/assets/system_skills/public/` without another copy operation.

Resolve pack selection in this order:

1. Packs explicitly named by the user.
2. The selected packs derived from a current `houmao-skill-config.json`.
3. `admin` for a clean target with no current config.

Project-local coding assistants are operator surfaces by default, so a new target receives the admin pack. Managed Houmao agents receive the agent pack through managed launch and are outside this routine unless the user explicitly selects `agent`.

Pass each pack explicitly during refresh. Do not rely on the CLI's omitted-pack default when preserving an existing combined or agent-only installation.

## Current Config and Legacy Receipt Handling

The current ownership file is:

```text
<project-home>/.houmao/system-skills/<tool>/houmao-skill-config.json
```

Use `pixi run houmao-mgr --print-json system-skills status --tool <tool> --home <absolute-project-home>` to classify it.

- For `config.status == "current"`, use `upgrade`.
- For `config.status == "absent"` with no selected destination paths, use `install`.
- For corrupt or unsupported current config, stop and report the config path and diagnostic.
- For an old `receipt.json`, treat the receipt as stale metadata only. It does not authorize replacement.
- For absent current config with existing selected destinations, report unowned collisions and require explicit user approval before removing or replacing exact paths.

After approval, inspect each colliding root. Preserve a backup of modified real directories, remove only the approved Houmao roots, and run a clean `install`. Removing the stale receipt is optional, but report whether it remains.

## Development Skill Policy

Development skills are immediate child directories of `<checkout>/skillset/dev/` that contain `SKILL.md`. They are outside the packaged system-skill config.

For each selected skill root:

1. Build the existing development-skill set by matching top-level entry names against valid source directories.
2. Preserve every existing development skill unless the user explicitly requests its removal.
3. Refresh an existing symlink to the absolute matching source directory when its target is broken, relative, or points at another checkout.
4. Add an absent development skill only when the user names it or requests all development skills.
5. Preserve a real directory and ask before replacing it with a symlink.
6. Remove only explicitly requested development skills.

Leave OpenSpec skills, third-party skills, and every other unmatched entry untouched.

## Verification Contract

For every selected target:

1. Run the structured `system-skills status` command again with the exact tool and home.
2. Require the selected packs and members to report `complete`, current config schema `houmao-skill-config.v1`, and projection mode `symlink`.
3. Confirm every preserved or requested development skill resolves to its absolute source under `<checkout>/skillset/dev/`.
4. Confirm no unrelated skill-root entry changed.
5. Run `system-skills doctor` when an exact release-version match is expected.

A commit-stamped editable package such as `2.1.0+local.<commit>` intentionally differs from the release-only `houmao_version` in source skill frontmatter. Doctor will report `mismatch` even when current-source content and config integrity are complete. Report that diagnostic; do not rewrite release frontmatter to conceal it.

## Output Contract

State the checkout and selected project homes first. For each home, report the tool, packs, config path and status, packaged roots refreshed, development skills preserved or changed, legacy receipt posture, verification result, and any approval blocker.

## Guardrails

- DO NOT omit `--home` for a project-local update.
- DO NOT infer pack selection or ownership from an old `receipt.json`.
- DO NOT overwrite a conflicting or modified unowned root without explicit approval.
- DO NOT install the agent pack into an operator home unless the user requests it or a current config already owns it.
- DO NOT replace a real development-skill directory without explicit approval.
- DO NOT remove unrelated, third-party, OpenSpec, or omitted development skills.
- DO NOT rewrite packaged `houmao_version` frontmatter to match a temporary local package version.
