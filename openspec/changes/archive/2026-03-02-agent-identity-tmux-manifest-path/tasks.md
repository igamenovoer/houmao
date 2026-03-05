## 1. CLI Surface and Identity Parsing

- [x] 1.1 Replace `--session-manifest` with `--agent-identity` for `send-prompt` and `stop-session` (update help text and JSON output expectations).
- [x] 1.2 Add optional agent naming input at CAO session start (for example `start-session --agent-identity <name>` restricted to `backend=cao_rest`).
- [x] 1.3 Implement deterministic identity parsing for `--agent-identity` (path-like vs name) plus normalization (exact `AGENTSYS-` prefix match only; no case conversion) and warnings for inexact `AGENTSYS` look-alikes (case-insensitive substring match when prefix is missing).
- [x] 1.4 Implement agent name validation rules: restrict to tmux+filesystem-safe chars (ASCII letters/digits plus `_` and `-`) and reject a standalone `AGENTSYS` token in the name portion (token boundaries `[^0-9A-Za-z]` and string boundaries).
- [x] 1.5 Add structured `start-session` output field that returns the selected canonical identity for CAO sessions.

## 2. CAO/tmux Session Naming and Manifest Pointer

- [x] 2.1 Reorder session start flow so the session manifest path is allocated early enough to be written into tmux env during tmux session creation.
- [x] 2.2 Update CAO backend tmux session naming to use the canonical agent identity (`AGENTSYS-...`) instead of the current timestamp/uuid-generated `cao-...` format.
- [x] 2.3 Set tmux session env var `AGENTSYS_MANIFEST_PATH` to the absolute session manifest path for tmux-backed sessions.
- [x] 2.4 Implement auto-generated agent names for unnamed CAO sessions (short tool+role/blueprint-derived base + conflict-avoiding suffix) and enforce explicit-name uniqueness.

## 3. Name-Based Resume and Control

- [x] 3.1 Implement name-based resolution for `--agent-identity <name>` using tmux: locate the tmux session and read `AGENTSYS_MANIFEST_PATH`.
- [x] 3.2 Add fail-fast, actionable errors for missing tmux session, missing/blank `AGENTSYS_MANIFEST_PATH`, missing manifest file, or manifest mismatch (manifest `cao.session_name` must match the addressed tmux session name).
- [x] 3.3 Ensure CAO prompt/stop operations still use only persisted session-manifest fields for CAO addressing (no base URL override at resume time).

## 4. Demos and Documentation

- [x] 4.1 Update `scripts/demo/**` to use `--agent-identity` instead of `--session-manifest`.
- [x] 4.2 Update runtime docs to explain the `AGENTSYS-` naming convention, reserved keyword, and how to discover agents via `tmux ls`.

## 5. Validation and Tests

- [x] 5.1 Add unit tests for agent-identity parsing and normalization (path-like detection, prefixing, reserved keyword).
- [x] 5.2 Add unit tests for validation rules: allowed character set, standalone-token `AGENTSYS` rejection, and inexact-look-alike warning emission.
- [x] 5.3 Add unit tests for tmux env pointer read/write behavior (mock `tmux` subprocess calls).
- [x] 5.4 Add regression tests validating `start-session` returns the selected canonical identity for CAO sessions.
