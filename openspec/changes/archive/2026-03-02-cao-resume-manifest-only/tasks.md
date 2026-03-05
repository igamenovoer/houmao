## 1. Remove CAO base URL overrides for resume (BREAKING)

- [x] 1.1 Remove `--cao-base-url` from `send-prompt` and `stop-session` CLI argument parsing and update help text
- [x] 1.2 Remove resume-time CAO base URL override from `resume_runtime_session(...)` (signature + call sites)
- [x] 1.3 Ensure CAO resume uses `session_manifest.cao.api_base_url` only (no fallback/override), add invariant check `cao.api_base_url == backend_state.api_base_url`, and treat missing/blank/mismatched CAO manifest fields as `SessionManifestError`

## 2. Update docs and in-repo call sites

- [x] 2.1 Update `docs/reference/brain_launch_runtime.md` to reflect manifest-only addressing for CAO resumed operations
- [x] 2.2 Update CAO demo scripts to stop passing `--cao-base-url` to resumed operations (`send-prompt`, `stop-session`)
- [x] 2.3 Update `scripts/demo/cao-claude-esc-interrupt/scripts/interrupt_driver.py` to read CAO base URL from the session manifest (remove/avoid a separate `--cao-base-url`)

## 3. Tests and verification

- [x] 3.1 Add hermetic unit tests that resume constructs the CAO client/session from the manifest URL (use a non-default `cao.api_base_url` and assert there is no override path)
- [x] 3.2 Add unit test that an inconsistent CAO manifest (`cao.api_base_url` != `backend_state.api_base_url`) fails fast with `SessionManifestError` (message includes `api_base_url`)
- [x] 3.3 Add unit test that a blank `cao.terminal_id` fails fast with `SessionManifestError` (message includes `terminal_id`)
- [x] 3.4 Keep unit CI hermetic: no live CAO integration tests; rely on demo packs/manual runs for end-to-end validation
- [x] 3.5 Run `pixi run ruff format .`, `pixi run ruff check .`, `pixi run mypy src`, and `pixi run python -m pytest` (or targeted subset) for changed areas

## 4. Deferred follow-up (optional)

- [x] 4.1 (Optional) Remove `--cao-profile-store` from `send-prompt`/`stop-session` (keep on `start-session`) to keep “manifest pointer is enough” coherent; update docs/demos accordingly
