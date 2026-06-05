## Context

Houmao already has a shared tmux-backed headless runtime for Claude, Codex, and Gemini. The runtime launches a provider CLI for each turn, captures raw stdout and stderr, normalizes provider JSONL into canonical events, stores a provider session id for resume, and keeps the tmux pane inspectable.

Kimi Code CLI 0.10.1 is installed on this host at `/home/huangzhe/.kimi-code/bin/kimi`, but it is not on this shell's `PATH`. Its native prompt mode works with `kimi -p <prompt> --output-format stream-json`. Live probes showed assistant text, tool calls, tool results, and session resume metadata as JSONL. Kimi uses `KIMI_CODE_HOME` for config, sessions, credentials, logs, and update state. OAuth tokens are stored under `credentials/kimi-code.json`; `device_id` is generated on demand.

The current Houmao shared headless command builder does not fit Kimi resume syntax because it places base args before resume args. Kimi requires the prompt value immediately after `-p`; the valid command order is selector args first, then `-p <prompt>`, then `--output-format stream-json`.

## Goals / Non-Goals

**Goals:**

- Add a maintained `kimi_headless` backend that works through Kimi prompt mode.
- Preserve raw Kimi stdout and stderr while emitting canonical Houmao events for assistant text, tool calls, tool results, and session identity.
- Support new, exact-resume, and latest-resume turns using Kimi's native session selectors.
- Project Kimi runtime homes using `KIMI_CODE_HOME`, projected skills, OAuth credentials, and env-model credentials.
- Support Kimi model aliases through launch-owned model selection.
- Include Kimi in server-managed headless launch and follow-up surfaces.

**Non-Goals:**

- Do not implement Kimi ACP integration in this change.
- Do not implement Kimi interactive TUI state tracking in this change.
- Do not preserve compatibility with removed Houmao CLI surfaces.
- Do not migrate existing Claude, Codex, or Gemini sessions.

## Decisions

### Use native Kimi prompt mode for the first backend

Kimi prompt mode already provides the required non-interactive surface: `-p`, `--output-format stream-json`, `--session <id>`, `--continue`, `--model <alias>`, and `--skills-dir`. This keeps the first integration close to existing headless backends and avoids pulling ACP into the runtime path before Houmao has a reason to own that protocol.

Alternative considered: implement Kimi ACP first. ACP is a useful future path, but it would introduce a different process protocol and auth behavior before the simpler prompt-mode path is exhausted.

### Add a Kimi-specific command builder

`KimiHeadlessSession` will mirror Gemini's command-placement override. It will build:

- new turn: `kimi -p <prompt> --output-format stream-json`
- exact resume: `kimi --session <session_id> -p <prompt> --output-format stream-json`
- latest resume: `kimi --continue -p <prompt> --output-format stream-json`

Kimi's hidden `-r <id>` works in clean live probes, and Kimi's resume hint prints that form, but Houmao will use public `--session <id>` for exact resume. The backend will not add `--auto`, `--yolo`, or `--plan` because Kimi rejects those flags with prompt mode and internally forces prompt sessions into auto permission handling.

Alternative considered: reuse the shared base command builder. A live probe showed the resulting `kimi -p --session <id> <prompt>` form fails, so the shared builder would make resume unusable.

### Treat Kimi JSONL as a first-class provider stream

The canonical parser will add provider `kimi`. It will parse Kimi's stream JSON as follows:

- `{"role":"assistant","content":...}` becomes canonical `assistant`.
- `{"role":"assistant","tool_calls":[...]}` becomes canonical `action_request` events. Function arguments are parsed from JSON strings when possible and otherwise preserved as raw text.
- `{"role":"tool","tool_call_id":...,"content":...}` becomes canonical `action_result`.
- `{"role":"meta","type":"session.resume_hint","session_id":...}` becomes canonical `session` and updates the parser session id.
- Unknown Kimi payloads remain passthrough or diagnostic events.

Kimi does not emit a provider completion event in normal prompt mode. Houmao will rely on the existing runner process-exit completion path and final session event rather than inventing provider usage data.

Alternative considered: coerce Kimi events through the Claude or Gemini parser. The JSON shape is OpenAI-chat-like and does not match either parser, so a dedicated provider parser is clearer and safer.

### Project deterministic Kimi homes

The Kimi adapter will use `KIMI_CODE_HOME` and default `launch.executable: kimi`. Host-specific absolute executable paths can be supplied through local adapter/profile overrides. The default starter adapter must not embed `/home/huangzhe/.kimi-code/bin/kimi`.

Houmao will project selected skills under `<home>/skills` and pass `--skills-dir <home>/skills` for managed Kimi prompt mode. This prevents Kimi from also loading the operator's generic `~/.agents/skills` path during managed launches.

OAuth bundles will project `config.toml` plus `credentials/`, or at least `credentials/kimi-code.json`. Env-model bundles will allow the `KIMI_MODEL_*` family. Plain `KIMI_API_KEY` is not a supported shell credential path for Kimi Code prompt mode and will not be treated as the primary contract.

Alternative considered: let Kimi auto-discover skills and user-global home state. That would make managed homes non-hermetic and would couple tests to the operator's personal setup.

### Keep model selection simple

For Kimi config-backed or OAuth-backed homes, launch-owned model names will project as final CLI args `--model <alias>`. Live probing confirmed `--model kimi-code/kimi-for-coding` works with prompt mode.

For env-model credentials, `KIMI_MODEL_NAME` remains an auth/runtime input. If the implementation can detect env-model auth cleanly, a launch-owned model override may update the projected `KIMI_MODEL_NAME`; otherwise the first implementation should reject conflicting Kimi model override attempts with a clear message instead of silently passing an alias that is not present in Kimi config.

Alternative considered: always write `default_model` into `config.toml`. That risks mixing config-backed and env-model flows and can conflict with OAuth-managed provider config.

## Risks / Trade-offs

- Kimi is not guaranteed to be on `PATH` on this host -> Allow adapter/profile executable overrides and keep launch-policy version probing compatible with absolute executable paths.
- Kimi prompt mode has no final usage event -> Preserve raw artifacts and canonical semantic events, and use process exit for turn completion until Kimi exposes usage in stream JSON.
- Kimi skill auto-discovery could load user-global skills -> Add `--skills-dir <home>/skills` for managed Kimi launches.
- OAuth config can be misprojected by mixing `api_key` and `oauth` on the same provider -> Preserve auth-bundle config as authored and do not synthesize mixed provider auth.
- Existing backend allowlists are spread across runtime, server, schemas, launch overrides, and docs -> Update allowlists through tests that launch and resume a fake Kimi executable.

## Migration Plan

This is an additive change. Existing Claude, Codex, and Gemini launch behavior should remain unchanged. Rollback is to remove the Kimi adapter, launch policy registry entry, backend enum entries, parser branch, and related schema additions.

## Open Questions

- Should the first implementation support env-model launch-owned model overrides by mutating `KIMI_MODEL_NAME`, or should it reject those overrides until a focused follow-up?
- Should `--skills-dir <home>/skills` be a backend-owned required arg for all managed Kimi launches, or should launch overrides be allowed to replace it for advanced users?
