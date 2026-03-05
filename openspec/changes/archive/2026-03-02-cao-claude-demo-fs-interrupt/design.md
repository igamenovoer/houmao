## Context

We already have a CAO-backed Claude Code backend (`cao_rest`) that drives the terminal through tmux and extracts answers via “shadow parsing” of `mode=full` scrollback (see `docs/reference/cao_claude_shadow_parsing.md`). The existing demo pack (`scripts/demo/cao-claude-session/`) validates a single prompt/response round-trip, but it does not validate:

- filesystem effects (Claude actually writes files under `tmp/...`), and
- resilience to user intervention in the live tmux UI (e.g. pressing `Esc` mid-turn).

Constraints:

- The demos must be safe to run locally (no modifying tracked files) and should default to writing under `tmp/`.
- The demos should be self-contained, reproducible, and follow existing `scripts/demo/*` conventions (SKIP behavior, `--snapshot-report`, and a sanitized `report.json` verifier).
- The “press Esc” behavior cannot rely on CAO’s `/exit` endpoint because CAO’s provider `exit_cli()` for `claude_code` is `"/exit"` (text command), not an `Escape` keypress.

## Goals / Non-Goals

**Goals:**

- Add two new demo packs under `scripts/demo/`:
  - `cao-claude-tmp-write`: prompt Claude Code to create a deterministic code file under a unique `tmp/<subdir>/...` and verify it exists and runs.
  - `cao-claude-esc-interrupt`: submit a “long-ish” prompt, confirm the terminal enters `processing`, send `Esc` via tmux to interrupt, then send a second prompt and verify the session still works.
- Ensure both demos:
  - SKIP cleanly when prerequisites are missing (credentials, CAO connectivity, tmux),
  - emit helpful debugging breadcrumbs (terminal id, CAO terminal pipe log path),
  - keep all artifacts under `tmp/` and avoid tracked-file modifications.

**Non-Goals:**

- Modifying runtime backend behavior (e.g., changing `CaoRestSession.send_prompt()` semantics).
- Extending the CAO server API (e.g., adding a REST endpoint for `send_special_key`).

## Decisions

1. **Demo structure mirrors existing CAO demos**
   - Follow `scripts/demo/cao-claude-session/` conventions: `README.md`, `run_demo.sh`, `inputs/`, `scripts/verify_report.py`, `expected_report/report.json`.
   - Reuse the existing `run_demo.sh` pattern for:
     - creating a unique workspace under `tmp/demo_*`,
     - optional auto-start/stop of local `cao-server`,
     - consistent SKIP classification for missing creds / connectivity / timeouts.

2. **`tmp/<subdir>` writes use repo-root workdir + path templating**
   - Start the session with `--workdir "$REPO_ROOT"` so prompt paths like `tmp/<subdir>/hello.py` are unambiguous.
   - In `run_demo.sh`, compute a unique subdir under `tmp/` and interpolate it into the prompt (template replacement) so the verifier can deterministically locate the output file.
   - Verification checks:
     - file exists,
     - file contains a sentinel string,
     - running `python <file>` prints the sentinel.
   - Guardrail: verify `git diff --name-only` is empty after the run to ensure tracked files were not modified.

3. **Esc interrupt is implemented via tmux (local-only)**
   - Because CAO does not expose `send_special_key` over REST, the demo sends `Esc` directly via tmux:
     - Use CAO `GET /terminals/{id}` to get the tmux window name (`terminal.name`).
     - Use the runtime session manifest (or the same CAO terminal response) to get `session_name`.
     - Execute `tmux send-keys -t "${session_name}:${window_name}" Escape`.
   - This requires the CAO tmux server to be on the same host as the demo script, so the demo should SKIP unless `CAO_BASE_URL` is local default (or another explicitly allowed “local” URL).

4. **Interrupt orchestration uses a small Python driver (not `send-prompt`)**
   - `agent_system_dissect.agents.brain_launch_runtime send-prompt` blocks until the shadow parser sees `completed`; an `Esc` interrupt may return Claude Code to `idle` without emitting a new response marker, which would cause `send-prompt` to time out.
   - The interrupt demo therefore uses a Python helper script that:
     - uses `CaoRestClient` + `ClaudeCodeShadowParser` to poll `mode=full`,
     - waits for `processing`, sends `Esc`, then waits for `idle`,
     - submits a second prompt and waits for `completed`, then extracts the answer using `ClaudeCodeShadowParser.extract_last_answer()`.

## Risks / Trade-offs

- **[Claude Code UI drift]** spinner/prompt/marker changes may make it hard to detect `processing` or `idle` reliably → Mitigation: use the existing `ClaudeCodeShadowParser` for status classification and keep prompts small.
- **[Interrupt semantics differ]** `Esc` may not cancel generation in some versions or may open a menu → Mitigation: treat “could not observe processing” / “did not return to idle” as SKIP with debug breadcrumbs (terminal log path).
- **[Remote CAO servers]** tmux key injection and local filesystem verification won’t work when CAO runs remotely → Mitigation: explicitly SKIP unless CAO is local.

