## 1. Runtime Launch and Managed Kimi Skill Discovery

- [x] 1.1 Update `houmao-mgr project agents launch` so Kimi specialists and Kimi-backed profiles can launch without `--headless`, while Gemini still fails clearly without `--headless`.
- [x] 1.2 Add or update project command tests for Kimi specialist TUI launch, Kimi profile TUI launch, explicit Kimi `--headless`, and Gemini required-headless rejection.
- [x] 1.3 Add managed Kimi `config.toml` handling so projected managed skill roots are added to `extra_skill_dirs` for Kimi runtime homes without overwriting unrelated config values or duplicating entries.
- [x] 1.4 Add managed Kimi construction or launch-preparation tests proving `extra_skill_dirs` is written, existing Kimi config is preserved, duplicate entries are avoided, and local-interactive Kimi launch does not receive a Houmao-injected `--skills-dir`.

## 2. System-Skills CLI Behavior

- [x] 2.1 Verify and repair `houmao-mgr system-skills install`, `status`, and `uninstall` support for `--tool kimi`, including single-tool, comma-separated multi-tool, omitted-home, `KIMI_CODE_HOME`, and explicit-home paths.
- [x] 2.2 Update human-readable Kimi install/status/uninstall output so it reports effective home and projected skill paths without claiming arbitrary `<KIMI_CODE_HOME>/skills` is auto-discovered by Kimi Code.
- [x] 2.3 Add or update system-skills CLI tests for Kimi home resolution, projection paths, multi-tool output, status discovery, uninstall cleanup, and the discovery caveat where output is user-facing.

## 3. Packaged System Skills

- [x] 3.1 Update `houmao-credential-mgr` top-level and action guidance to include Kimi credential `list`, `get`, `add`, `set`, `rename`, and `remove`, while keeping credential `login` helper guidance limited to Claude, Codex, and Gemini.
- [x] 3.2 Add `houmao-credential-mgr/references/kimi-credential-kinds.md` with Kimi credential input kinds and credential-manager flag spellings, then update the credential kinds menu and add/set guidance to cite it.
- [x] 3.3 Repair `houmao-agent-definition` credential reference links for Claude, Codex, Gemini, and Kimi so installed skill links resolve and do not point at missing local files.
- [x] 3.4 Update `houmao-agent-definition` specialists, profiles, create-agent-fast-forward, and launch-agent guidance so Kimi examples use tool `kimi`, Kimi launch posture defaults to TUI/local-interactive when unspecified, and Gemini remains the required-headless exception.
- [x] 3.5 Update adjacent packaged guidance such as `houmao-touring` and any launch lifecycle pages that still list only Claude, Codex, and Gemini or describe Kimi as unavailable/headless-only.

## 4. Documentation

- [x] 4.1 Update `docs/reference/cli/system-skills.md` so Kimi appears in supported tool lists, home resolution, projection paths, status/install/uninstall examples, and projection-versus-discovery caveats.
- [x] 4.2 Update project launch and credential CLI reference material so Kimi project specialists/profiles are described as TUI-capable by default, Kimi credential CRUD flags are documented, and Kimi is not listed as a credential login-helper provider.
- [x] 4.3 Update `docs/getting-started/system-skills-overview.md` so Kimi external installs, `.kimi-code/skills`, `KIMI_CODE_HOME`, managed `extra_skill_dirs`, and headless-only `--skills-dir` behavior are described consistently.

## 5. Validation

- [x] 5.1 Add or update packaged skill content tests for Kimi support, Kimi credential references, broken relative-link prevention, and stale headless-only wording.
- [x] 5.2 Run focused unit tests for project commands, system-skills CLI behavior, brain construction or launch preparation, and packaged skill content.
- [x] 5.3 Run `pixi run lint`, `pixi run typecheck`, and `pixi run test`; record any unrelated pre-existing failures separately from this change.
