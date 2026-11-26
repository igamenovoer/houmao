# Profile Lanes and Qualified Run Modes

Houmao separates specialist-backed project profiles, recipe-backed project launch profiles, and native launch dossiers so authoring commands stay lane-bounded.

## Lane Comparison

| Lane | Subcommand | CLI Family | Source | Default Routing |
| --- | --- | --- | --- | --- |
| Project profile | `profiles` | `houmao-mgr project profile ...` | Project specialist | Default for `profile`, `agent profile`, `project profile`, or `ready profile` ([profiles.md](../../commands/easy/profiles.md), [create-agent-fast-forward.md](../../commands/easy/create-agent-fast-forward.md)); launched via `project agents launch --profile <name>`. |
| Recipe launch profile | `recipe-profiles` | `houmao-mgr project agents launch-profiles ...` | Low-level recipe | Used when a project launch profile is explicitly backed by a recipe/preset ([recipe-profiles.md](../../commands/low-level/recipe-profiles.md)). |
| Native launch dossier | `launch-dossiers` | `houmao-mgr internals native-agent launch-dossiers ...` | Low-level recipe | Used only when the caller explicitly names `launch-dossiers` or `internals native-agent launch-dossiers` ([launch-dossiers.md](../../commands/low-level/launch-dossiers.md)). |

Use `set` for routine patch edits, pass `--yes` on `create`/`add` only for intentional same-name replacement, and never cross-overwrite one lane with another.

## Qualified Run Modes

Use `--mode headless` (one CLI process per turn), `--mode service` (persistent structured request protocol), `--mode tui` (interactive terminal UI), or `--mode web` (native browser/ACP UI). Profiles persist `defaults.posture.mode`; a launch-level `--mode` overrides it for that single instance only.

| Tool | Project Default | Qualified Modes |
| --- | --- | --- |
| Claude (`claude`) | `tui` | `headless`, `tui` |
| Codex (`codex`) | `tui` | `headless`, `service`, `tui` |
| Kimi (`kimi`) | `tui` | `headless`, `service`, `tui`, `web` |
| DSH (`dsh`) | `web` | `headless`, `service`, `web` |

Report the CLI's unsupported-mode diagnostic if an unqualified combination is requested. Select `--prompt-mode unattended|as_is` independently of `--mode`, and use `--headless-display-style [plain|json|fancy]` / `--headless-display-detail [concise|detail]` when customizing live pane rendering for `headless` sessions.
