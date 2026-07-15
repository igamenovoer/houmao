## 1. Core Projection and Target Resolution

- [x] 1.1 Add `universal` to the shared system-skill projection target map with destination root `skills`.
- [x] 1.2 Update system-skill target validation so supported targets are not inferred only from tool home environment-variable mappings.
- [x] 1.3 Update CLI effective-home resolution so omitted `--tool universal` resolves to `Path.home() / ".agents"` and explicit `--home` is treated as the root containing `skills/`.
- [x] 1.4 Preserve existing managed launch and managed join behavior so managed runtime installs still target only the selected runtime tool home.

## 2. Kimi and Universal User-Facing Semantics

- [x] 2.1 Keep `kimi` as the only Kimi selector and reject `kimi-code` before filesystem mutation with a diagnostic that tells operators to use `kimi` for Kimi Code CLI.
- [x] 2.2 Update `system-skills` help text to list `universal`, define `kimi` as Kimi Code CLI, and warn that `kimi` is not the legacy MoonshotAI `kimi-cli`.
- [x] 2.3 Replace the stale Kimi discovery note with wording that explains `--home` places files and Kimi Code discovers them when launched with the matching `KIMI_CODE_HOME`, `--skills-dir`, or `extra_skill_dirs`.
- [x] 2.4 Add a concise universal plain-output note or projection output path that makes the concrete `~/.agents/skills` target clear without implying that Houmao configures every client.

## 3. Documentation

- [x] 3.1 Update `docs/reference/cli/system-skills.md` for `universal`, Kimi Code CLI naming, legacy `kimi-cli` warning, and corrected Kimi discovery semantics.
- [x] 3.2 Update `docs/reference/cli/houmao-mgr.md` and any system-skill overview references that enumerate supported system-skill targets.
- [x] 3.3 Ensure docs describe `--home` for `universal` as the `.agents` root that contains `skills/`, not as the `skills/` directory itself.

## 4. Tests

- [x] 4.1 Add shared installer tests for `universal` copy projection, symlink projection, status discovery, and uninstall behavior under `skills/`.
- [x] 4.2 Add CLI tests for omitted-home universal resolution using patched HOME, explicit universal `--home`, and comma-separated multi-target install/uninstall including `universal`.
- [x] 4.3 Add CLI tests that `kimi-code` is rejected before mutation and that help text defines `kimi` as Kimi Code CLI, warns about legacy `kimi-cli`, and lists `universal`.
- [x] 4.4 Update Kimi plain-output and documentation tests so they no longer assert that `$KIMI_CODE_HOME/skills` is not automatically discovered by Kimi Code.

## 5. Validation

- [x] 5.1 Run focused unit tests for system-skill installer and `houmao-mgr system-skills` command behavior.
- [x] 5.2 Run focused docs tests that cover system-skill CLI reference text.
- [x] 5.3 Run Ruff on edited Python tests and implementation files.
- [x] 5.4 Run OpenSpec apply-readiness validation for `support-universal-system-skill-install`.
