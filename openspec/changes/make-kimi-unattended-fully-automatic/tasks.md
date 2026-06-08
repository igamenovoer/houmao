## 1. Launch Policy Registry and Hooks

- [ ] 1.1 Add a maintained Kimi unattended `raw_launch` strategy to `src/houmao/agents/launch_policy/registry/kimi.yaml`, version-scoped to the supported Kimi TUI family and distinct from the existing `kimi_headless` prompt-mode strategy.
- [ ] 1.2 Declare Kimi TUI unattended owned state in the registry, including `config.toml` key `default_permission_mode` and evidence from `extern/orphan/kimi-code` for `--auto`, `default_permission_mode`, `/auto on`, and resumed-startup flag conflicts.
- [ ] 1.3 Add or split provider hooks so Kimi raw-launch unattended canonicalization removes caller-owned low-level permission/session startup flags without relying on persistent `--auto` in final TUI commands.
- [ ] 1.4 Ensure launch-policy TOML mutation can set `default_permission_mode = "auto"` while preserving unrelated Kimi config keys and existing `extra_skill_dirs`.
- [ ] 1.5 Add launch-policy tests proving Kimi `raw_launch` with `operator_prompt_mode = unattended` selects the new strategy, writes `default_permission_mode = "auto"`, strips conflicting low-level Kimi args, and leaves Kimi `as_is` untouched.
- [ ] 1.6 Add regression tests proving existing Kimi `kimi_headless` unattended launch behavior still strips prompt-mode-incompatible flags and does not require TUI-only startup state.

## 2. Kimi Local-Interactive Runtime Behavior

- [ ] 2.1 Add launch-plan or manifest metadata needed by `local_interactive` runtime to determine whether a Kimi TUI session resolved `operator_prompt_mode = unattended`.
- [ ] 2.2 Implement a Kimi local-interactive startup refresh that submits `/auto on` after TUI readiness and before Houmao role bootstrap or workload prompts when unattended mode is active.
- [ ] 2.3 Apply the same Kimi auto-mode refresh after local-interactive relaunch, including relaunches that resume provider history with `--continue` or `--session <session_id>`.
- [ ] 2.4 Keep the existing Kimi relaunch guard that rejects final commands combining `--continue` or `--session <session_id>` with `--auto`, `--yolo`, or `--plan`.
- [ ] 2.5 Make Kimi unattended TUI launch or relaunch fail clearly if the auto-mode refresh cannot be submitted, instead of continuing with manual approval prompts.
- [ ] 2.6 Add runtime tests for fresh unattended Kimi TUI startup order, resumed Kimi TUI startup order, failure diagnostics, and `as_is` launches not sending `/auto on`.

## 3. Project Launch and Demo Flow

- [ ] 3.1 Add or update project CLI tests proving Kimi specialists and Kimi-backed project profiles with stored `launch.prompt_mode: unattended` launch through local-interactive posture without forcing `--headless`.
- [ ] 3.2 Add or update project CLI tests proving Kimi specialists and profiles with stored `launch.prompt_mode: as_is` do not request Kimi auto mode.
- [ ] 3.3 Update `scripts/demo/kimi-writer-team-manual` so visible Kimi TUI agents that are expected to run automatically use unattended prompt mode rather than `--no-unattended`.
- [ ] 3.4 Update demo tests and README text to describe the expected fully automatic Kimi TUI unattended posture and the separate headless review posture when still used.

## 4. Documentation

- [ ] 4.1 Update the launch-policy reference to document separate Kimi headless and Kimi TUI unattended contracts, including why TUI unattended uses auto mode without persistent `--auto` launch args.
- [ ] 4.2 Update run-phase backend and relaunch docs to describe Kimi TUI unattended startup, `/auto on` resumed-session refresh, `--continue` / `--session` conflicts with `--auto`, and `as_is` behavior.
- [ ] 4.3 Update CLI reference material so Kimi automation points to `launch.prompt_mode: unattended` and does not present `--yolo` as a live Houmao launch option.
- [ ] 4.4 Update adjacent packaged system-skill guidance if it describes Kimi unattended, Kimi TUI launch posture, or raw Kimi permission flags.

## 5. Validation

- [ ] 5.1 Run focused launch-policy tests for Kimi raw-launch and headless unattended behavior.
- [ ] 5.2 Run focused local-interactive runtime tests for Kimi startup, relaunch, and auto-mode refresh behavior.
- [ ] 5.3 Run focused project CLI and demo-pack tests that cover Kimi unattended TUI launch posture.
- [ ] 5.4 Run `pixi run lint`, `pixi run typecheck`, and `pixi run test`.
- [ ] 5.5 Run `openspec status --change make-kimi-unattended-fully-automatic` and resolve any artifact or task tracking issues.
