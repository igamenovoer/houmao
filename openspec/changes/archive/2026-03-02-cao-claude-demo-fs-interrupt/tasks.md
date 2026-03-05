## 1. Add `cao-claude-tmp-write` demo pack

- [x] 1.1 Create `scripts/demo/cao-claude-tmp-write/` skeleton (`README.md`, `run_demo.sh`, `inputs/`, `scripts/verify_report.py`, `expected_report/report.json`)
- [x] 1.2 Implement `run_demo.sh` by adapting `scripts/demo/cao-claude-session/run_demo.sh` (workspace under `tmp/`, CAO health + local auto-start, credentials SKIP, build-brain/start-session/send-prompt/stop-session)
- [x] 1.3 Add prompt templating so Claude is instructed to write a deterministic runnable file at `tmp/<unique_subdir>/hello.py` and to avoid modifying tracked files
- [x] 1.4 Add verification steps: file exists, `python tmp/<unique_subdir>/hello.py` prints sentinel, and `git diff --name-only` is empty
- [x] 1.5 Emit a sanitized `report.json` (include file path + sentinel result) and ensure `scripts/verify_report.py` supports `--snapshot`

## 2. Add `cao-claude-esc-interrupt` demo pack

- [x] 2.1 Create `scripts/demo/cao-claude-esc-interrupt/` skeleton (`README.md`, `run_demo.sh`, `inputs/`, `scripts/verify_report.py`, `expected_report/report.json`)
- [x] 2.2 Implement a small Python driver script that uses `CaoRestClient` + `ClaudeCodeShadowParser` to: submit a “long-ish” prompt, wait for `processing`, send `Esc` via `tmux send-keys -t session:window Escape`, wait for `idle`, then submit a second prompt and extract a non-empty answer
- [x] 2.3 In the driver, resolve the tmux target by calling `GET /terminals/{id}` to obtain `window_name` (`terminal.name`) and record `terminal_id` + log path `~/.aws/cli-agent-orchestrator/logs/terminal/<terminal_id>.log`
- [x] 2.4 Wire `run_demo.sh` to build brain/start session, invoke the driver, stop session, write `report.json`, and verify with `scripts/verify_report.py`
- [x] 2.5 Ensure explicit local-only SKIP behavior (non-local `CAO_BASE_URL`) and a “could not observe processing” SKIP path to avoid flakes

## 3. Demo quality pass

- [x] 3.1 Ensure both demo `README.md` files document prerequisites, local-only constraints, and how to debug by attaching to tmux / reading the CAO terminal pipe log
- [x] 3.2 Run both demos locally and update `expected_report/report.json` via `--snapshot-report` if needed
