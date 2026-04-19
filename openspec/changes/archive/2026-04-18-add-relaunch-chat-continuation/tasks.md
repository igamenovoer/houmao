## 1. Selector Model and CLI Plumbing

- [x] 1.1 Add a relaunch chat-session selector model with modes `new`, `tool_last_or_new`, and `exact`, including validation that `exact` requires a provider session id.
- [x] 1.2 Add `houmao-mgr agents relaunch` options for relaunch chat-session mode and exact provider session id while preserving current-session and explicit target forms.
- [x] 1.3 Pass the parsed relaunch selector through managed-agent helper routing and `RuntimeSessionController.relaunch()`.
- [x] 1.4 Preserve omitted-selector behavior as `new` so existing relaunch commands remain fresh-chat relaunches.

## 2. Runtime Relaunch Behavior

- [x] 2.1 Extend local interactive relaunch command construction to accept an optional relaunch chat-session selector.
- [x] 2.2 Implement provider-native TUI selector translation for Codex, Claude Code, and Gemini CLI latest/exact continuation.
- [x] 2.3 Suppress bootstrap-message role injection when local interactive relaunch resumes an existing provider chat.
- [x] 2.4 Extend native headless relaunch handling so the selector becomes the startup/default selection for the next managed headless prompt.
- [x] 2.5 Preserve current manifest-first relaunch authority and tmux window `0` behavior for all selector modes.

## 3. Launch-Profile Relaunch Policy

- [x] 3.1 Add optional relaunch chat-session policy fields to the shared launch-profile catalog model and validation.
- [x] 3.2 Add create, patch, replace, inspect, and compatibility-projection support for stored relaunch chat-session policy.
- [x] 3.3 Apply launch-profile relaunch policy to future managed instances created from the profile without affecting first-launch provider startup.
- [x] 3.4 Ensure direct relaunch command selectors override any stored launch-profile relaunch default for that relaunch request.

## 4. Tests

- [x] 4.1 Add CLI tests for relaunch selector parsing, exact-id validation, default `new` behavior, and explicit/current-session target routing.
- [x] 4.2 Add runtime unit tests for TUI provider command translation across Codex, Claude Code, and Gemini CLI.
- [x] 4.3 Add headless runtime tests proving relaunch selector is applied to the next prompt command for latest and exact modes.
- [x] 4.4 Add launch-profile catalog tests for create, patch, replace, inspect, projection, and launch-to-runtime propagation.
- [x] 4.5 Add regression tests proving bootstrap-message role injection is not submitted into resumed TUI relaunch chats.

## 5. Docs and Skills

- [x] 5.1 Update CLI reference docs for `houmao-mgr agents relaunch` chat-session selector modes, exact id requirements, and examples.
- [x] 5.2 Update run-phase lifecycle/backend docs with provider-native TUI and headless continuation command mapping.
- [x] 5.3 Update launch-profile docs to explain relaunch-only chat-session policy and first-launch non-effect.
- [x] 5.4 Update the packaged `houmao-agent-instance` relaunch guidance to route continuation requests through Houmao relaunch.

## 6. Verification

- [x] 6.1 Run focused unit tests covering CLI, runtime relaunch, headless command construction, launch profiles, and system-skill docs.
- [x] 6.2 Run `pixi run lint` and any targeted type checks needed for changed modules.
- [x] 6.3 Perform a live or recorded TUI command-construction smoke where feasible, documenting any provider-auth limitations.
