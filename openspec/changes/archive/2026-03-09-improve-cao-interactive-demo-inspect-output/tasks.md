## 1. Inspect Surface Implementation

- [x] 1.1 Update `gig_agents.demo.cao_interactive_full_pipeline_demo` to derive `terminal_log_path` from the effective interactive-demo CAO home/launcher-home instead of the hard-coded user-home `~/.aws/...` convention.
- [x] 1.2 Add a best-effort CAO terminal-status lookup in `inspect` and expose it as `claude_code_state`, falling back to `unknown` when the live lookup is unavailable.
- [x] 1.3 Add `inspect --with-output-text <num-tail-chars>` so the demo fetches CAO `mode=full` output, projects clean Claude dialog text through the existing shadow parser path, and returns the requested character tail as `output_text_tail` without exposing raw scrollback.
- [x] 1.4 Rework the human-readable `inspect` output so it highlights session status, Claude Code state, operator commands, artifact locations, and the optional clean output-text tail while preserving the existing machine-readable inspection/report fields.

## 2. Documentation and Verification Contract

- [x] 2.1 Update `scripts/demo/cao-interactive-full-pipeline-demo/README.md` so the inspect examples and explanatory text describe the resolved per-run terminal-log location, the live `claude_code_state`, and the new `--with-output-text <num-tail-chars>` surface.
- [x] 2.2 Update `scripts/demo/cao-interactive-full-pipeline-demo/scripts/verify_report.py` and `expected_report/report.json` so the verification snapshot validates the resolved terminal-log-path contract instead of the legacy `~/.aws/...` prefix.

## 3. Regression Coverage

- [x] 3.1 Add or update unit tests covering default-path and overridden-launcher-home cases for `terminal_log_path`, live and failed `claude_code_state` lookup behavior, `--with-output-text` success and unavailability cases, and assertions for the revised human-readable inspect output.
- [x] 3.2 Run the relevant demo/unit validation to confirm `inspect` now prints a copy-pastable `tail -f` command that points at a real terminal log file in the active run and that `--with-output-text` returns a clean projected tail rather than raw TUI output.
