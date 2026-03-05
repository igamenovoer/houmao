## 1. Claude Brain Home Bootstrap

- [x] 1.1 Define Claude credential-profile state template input `agents/brains/api-creds/claude/<cred-profile>/files/claude_state.template.json` (local-only) and project it into the runtime home as `claude_state.template.json` (via `credential_projection.file_mappings`)
- [x] 1.2 Add a shared Claude home bootstrap helper that materializes runtime-home `.claude.json` by applying a selective overlay of launcher-enforced keys onto the template
- [x] 1.3 Ensure bootstrap is create-only (do not rewrite existing `.claude.json`) and validates `settings.json` contains `skipDangerousModePermissionPrompt: true`
- [x] 1.4 Invoke the bootstrap helper from all Claude launch paths (`cao_rest`, `claude_headless`, and any direct launcher entrypoints)
- [x] 1.5 Fail fast with actionable diagnostics when required `claude_state.template.json` template input is missing or malformed

## 2. Launch Invariants

- [x] 2.1 Ensure orchestrated Claude launches include a non-interactive bypass mechanism (for example `--dangerously-skip-permissions` or headless `-p`) without hardcoding upstream flags in backend code
- [x] 2.2 Make Claude headless base args tool-adapter-configurable via `agents/brains/tool-adapters/claude.yaml:launch.args`, with documented backend-reserved args and reserved-arg conflict detection (`--resume`, `--output-format`, `--append-system-prompt`)
- [x] 2.3 Update CAO/tmux session environment propagation to inherit the full calling process environment, then overlay credential-profile `vars.env`, then apply launch-specific env vars (and ensure `vars.env` injection is not gated by tool-adapter allowlists)

## 3. Tests

- [x] 3.1 Unit-test runtime `.claude.json` materialization from template when `ANTHROPIC_API_KEY` is set (enforced keys + approved suffix + no full key when key is longer than suffix length) and does not rewrite an existing `.claude.json`
- [x] 3.2 Unit-test runtime `.claude.json` materialization from template when `ANTHROPIC_API_KEY` is not set
- [x] 3.3 Unit-test template `mcpServers` entries are preserved in the final runtime `.claude.json` unless explicitly overwritten by enforced keys
- [x] 3.4 Unit-test launch fails with clear error when `claude_state.template.json` is missing/malformed
- [x] 3.5 Add/adjust a test that the Claude config profile projection includes `settings.json` with `skipDangerousModePermissionPrompt: true`
- [x] 3.6 Unit-test headless reserved-arg conflict detection in launch plan construction

## 4. Documentation & Validation

- [x] 4.1 Document the Claude non-interactive bootstrap contract and rationale (first-run prompts, feature-flag endpoint behavior)
- [x] 4.2 Run `scripts/demo/cao-claude-session/run_demo.sh` as an end-to-end validation and record the result in the change log or notes (including the tested Claude Code version)
