## Context

Houmao already has two related pieces of chat-session machinery:

- joined headless sessions can persist `resume_selection_kind = none | last | exact`,
- gateway/headless prompt control can select `chat_session.mode = auto | new | current | tool_last_or_new | exact`.

The missing surface is relaunch. `houmao-mgr agents relaunch` currently reuses the persisted home and manifest authority, but provider startup is rebuilt as a fresh chat. That is correct as the default, but it prevents an operator from using provider-native continuation during relaunch even though Codex, Claude Code, and Gemini CLI all expose startup resume flags for both TUI and headless modes.

The relevant provider-native forms are:

- Codex TUI: `codex resume --last`, `codex resume <session_id>`
- Codex headless: `codex exec resume --last <prompt>`, `codex exec resume <session_id> <prompt>`
- Claude TUI: `claude --continue`, `claude --resume <session_id>`
- Claude headless: `claude -p --continue <prompt>`, `claude -p --resume <session_id> <prompt>`
- Gemini TUI: `gemini --resume` / `gemini --resume latest`, `gemini --resume <session_id>`
- Gemini headless: `gemini --resume latest -p <prompt>`, `gemini --resume <session_id> -p <prompt>`

Relaunch continuation is runtime-owned. It should not rebuild the brain home, should not mutate an existing live provider process, and should not treat launch profile creation as live-session mutation.

## Goals / Non-Goals

**Goals:**

- Expose relaunch-time chat-session selection on `houmao-mgr agents relaunch`.
- Preserve current fresh-chat relaunch behavior unless an operator or launch profile explicitly requests continuation.
- Support Codex, Claude Code, and Gemini CLI provider-native continuation for both TUI and native headless managed sessions.
- Let launch profiles store a relaunch-only default chat-session policy for future instances.
- Keep prompt-control `chat_session` semantics and relaunch chat-session semantics aligned where they overlap.

**Non-Goals:**

- Do not add TUI gateway prompt continuation. The change concerns provider startup during relaunch, not prompt injection into an already-running TUI.
- Do not parse provider transcript stores to discover exact session ids.
- Do not automatically clear context, fork chats, or recover from provider corruption beyond using the selected provider-native startup mode.
- Do not change first-launch behavior for launch-profile-backed instances.

## Decisions

### Reuse the existing selector vocabulary

Relaunch will use `new`, `tool_last_or_new`, and `exact` as the portable selector modes. `new` means the existing fresh-chat relaunch behavior. `tool_last_or_new` delegates latest-chat selection to the provider CLI. `exact` requires an explicit provider session id.

Alternative considered: expose provider-specific names such as `--codex-last` or a generic `--resume-last`. That would make initial implementation simpler but would create a second selector model beside gateway/headless `chat_session`.

### Make continuation a relaunch selector, not a launch selector

Launch profiles may store a `relaunch.chat_session` policy, but that policy only applies to future relaunch of instances created from the profile. First launch remains fresh and uses the normal launch-profile birth-time fields.

Alternative considered: add a generic launch-profile `chat_session` field that affects first launch. That blurs birth-time launch configuration with provider history selection and would make profile creation capable of accidentally attaching a new instance to old provider context.

### Translate continuation at provider command construction

For TUI relaunch, `local_interactive` command construction will accept an optional relaunch chat-session selector and inject provider-native startup args before the provider process is respawned.

For native headless relaunch, the relaunch operation does not immediately run a provider turn. It will update the headless startup/default selector so the next managed prompt uses the requested mode through the existing headless command builders.

Alternative considered: send `/resume` or equivalent slash commands after TUI startup. That is fragile, depends on prompt readiness and screen state, and cannot reliably select exact provider sessions across providers.

### Suppress bootstrap-message role injection when resuming a TUI chat

If TUI relaunch resumes an existing provider chat, Houmao must not submit its launch bootstrap message as a new user turn. Native provider resume should hydrate the prior conversation, and replaying the bootstrap would pollute that conversation.

Native CLI args that carry role injection, such as Codex developer instructions or Claude append-system prompt, may still be included where the provider supports them at startup. Bootstrap-message injection is the risky case because it is delivered through the chat input.

Alternative considered: always replay bootstrap so the resumed chat receives current managed instructions. That treats continuation like a new launch and defeats the user expectation of preserving provider context.

## Risks / Trade-offs

- Provider latest-chat selection is provider-owned and may use cwd filtering or provider-home ordering differently across tools. Mitigation: document that `tool_last_or_new` delegates to the provider and offer `exact` for deterministic selection.
- Exact session ids are provider-native ids and not always known to Houmao for TUI sessions. Mitigation: treat ids as operator-supplied strings and avoid pretending Houmao can discover them portably.
- Launch-profile relaunch defaults could surprise users if named too broadly. Mitigation: store the field under an explicit `relaunch` namespace and keep first launch unchanged.
- Headless relaunch selection is applied on the next prompt, not during the relaunch command itself. Mitigation: surface that in docs and state output where practical.
- Older manifests and profiles lack relaunch chat-session policy. Mitigation: default to `new`, preserving current behavior.

## Migration Plan

No data migration is required. Existing launch profiles and session manifests omit relaunch chat-session policy and continue using fresh-chat relaunch.

Implementation can roll out additively:

1. Add selector models and CLI parsing with default `new`.
2. Add provider command translation and headless next-prompt/startup-default handling.
3. Add launch-profile persistence/resolution for future instances.
4. Update docs and system-skill guidance.
5. Add focused unit tests and live-smoke guidance for provider command construction.

Rollback is to ignore or remove the new selector fields; existing sessions continue to relaunch as fresh chats.
