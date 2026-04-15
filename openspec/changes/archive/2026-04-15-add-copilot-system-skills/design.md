## Context

Houmao system skills are already packaged as directories under `src/houmao/agents/assets/system_skills/<skill>/` with top-level `SKILL.md` files and local supporting material. The shared installer in `src/houmao/agents/system_skills.py` resolves the packaged catalog and projects selected skills into a tool-native destination root. The CLI wrapper in `src/houmao/srv_ctrl/commands/system_skills.py` currently accepts `--tool claude|codex|gemini`, resolves the effective home with `--home`, a tool-native env var, or a project-scoped default, then calls the shared installer.

GitHub Copilot's skill model can consume `SKILL.md` directories from project or personal skill roots. This change only needs to make the existing Houmao-owned packaged skill set installable for Copilot. It does not add a Copilot launch backend, credential workflow, project recipe tool adapter, or new packaged skill catalog.

## Goals / Non-Goals

**Goals:**

- Add `copilot` as a supported explicit `system-skills install|status --tool` value.
- Keep the existing command shape: no `--scope` flag and no second Copilot-specific command family.
- Make omitted-home Copilot installs project into `.github/skills/<houmao-skill>/` from the current working directory.
- Allow explicit personal-home installs by passing `--home ~/.copilot`, which projects into `~/.copilot/skills/<houmao-skill>/`.
- Preserve existing copy/symlink behavior, named-set selection, explicit-skill selection, CLI-default selection, and status discovery for Copilot.

**Non-Goals:**

- Add Copilot as a managed launch tool under `.houmao/agents/tools/`.
- Add Copilot credential import, login, model mapping, launch policy, gateway attachment, or runtime backend support.
- Introduce dual writes to `.agents/skills` or any other generic alias root.
- Rewrite the Houmao system skills for cloud-only operation.

## Decisions

### Decision: Treat Copilot as another shared installer target

The shared installer already takes a string `tool` and maps it to a visible skill destination. Copilot should join that mapping with `skills` as the destination, keeping target paths as `<home>/skills/<houmao-skill>/`.

Alternatives considered:

- Add a separate Copilot installer. Rejected because it would duplicate catalog resolution, projection modes, owned-path cleanup, and status logic.
- Add Copilot-specific catalog entries. Rejected because the same packaged skill content is valid `SKILL.md` content for Copilot.

### Decision: Use `.github` as the project-scoped default home

For omitted `--home`, `--tool copilot` should resolve:

1. explicit `--home`
2. `COPILOT_HOME`
3. `<cwd>/.github`

With destination `skills`, the project default lands at `<cwd>/.github/skills/<houmao-skill>/`, which is the natural repository skill root for Copilot. Users who want a personal install can pass `--home ~/.copilot`, and users who want env redirection can set `COPILOT_HOME`.

Alternatives considered:

- Default to `<cwd>` plus destination `.github/skills`. Rejected because it makes Copilot the only tool whose destination includes the project-specific container and makes explicit personal installs awkward.
- Add `--scope project|personal`. Rejected because the current command surface has no scope concept and the user explicitly wants to avoid adding one.
- Default to `~/.copilot`. Rejected because existing tools use project-scoped defaults when no env redirect is present, and repo-local Copilot skills are the safer default for this project-oriented installer.

### Decision: Do not install into `.agents/skills`

Copilot can also discover generic `.agents/skills`, but Houmao should not maintain that as the Copilot target. The repository already moved Gemini-owned skills away from `.agents/skills` to avoid generic cross-tool leakage. Keeping Copilot on `.github/skills` for project installs and `~/.copilot/skills` for personal installs preserves a clear owner-specific root.

### Decision: Document runtime availability separately from skill discovery

Installing the skills into `.github/skills` can make them discoverable to Copilot surfaces that read repository skills. Some Houmao skills operate local `houmao-mgr`, tmux, gateway, mailbox, and credential surfaces. Documentation should distinguish discoverability from successful execution: Copilot cloud can discover repository skills, but operational use requires an environment where the referenced Houmao runtime resources are available.

## Risks / Trade-offs

- [Copilot cloud discovers skills but lacks local runtime resources] -> Document that operational commands require `houmao-mgr` and the relevant local/project resources in the execution environment.
- [Existing `.github/skills` may contain user-authored content] -> Reuse the installer's non-owned collision behavior so Houmao does not silently overwrite unrelated skill directories.
- [Operators may expect personal Copilot install by default] -> Document `--home ~/.copilot` and `COPILOT_HOME` for personal installs while keeping the project default consistent with existing tool defaults.
- [Symlinked project skills may not work in remote/cloud contexts] -> Preserve `--symlink` for local development, but keep copy projection as the default.
