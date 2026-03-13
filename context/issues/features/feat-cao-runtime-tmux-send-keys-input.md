# Feature Request: CAO Runtime tmux `send-keys` Input For Managed Agents

## Status
Proposed

## Summary
Add a runtime-supported tmux `send-keys` input mechanism for CAO-managed agents so callers can send special keys and control input to the live managed terminal, not just plain prompt text.

This is needed for interactive provider surfaces that cannot be driven correctly with normal text submission alone, including slash-command menus such as `/model` that require arrow-key navigation and confirmation.

## Why
Current CAO-backed runtime control is prompt-oriented:
- `realm_controller send-prompt` exposes only plain prompt text submission.
- `CaoRestSession.send_prompt()` submits text through CAO terminal input and then waits for readiness/completion.
- The runtime docs explicitly describe CAO-backed sessions as using direct terminal input only, with no first-class keypress/control-input API.

That works for normal prompt turns, but it breaks down for live interactive UI inside the managed agent:
- slash-command menus that need `Up` / `Down` / `Enter`,
- transient selection menus that require arrow-key navigation,
- interactive flows that need `Escape` to back out of a menu,
- provider-specific prompt surfaces where “type text and newline” is not equivalent to pressing a real terminal key.

We already have local proof that real key injection is useful: `scripts/demo/cao-claude-esc-interrupt/` uses `tmux send-keys ... Escape` to interrupt a Claude CAO session and continue the session afterward. That capability should be promoted into a supported runtime contract for managed agents rather than remaining a one-off local demo technique.

## Requested Scope
1. Add a runtime-level control-input mechanism for CAO-managed tmux-backed sessions that sends keys through tmux rather than through prompt-text submission.
2. Resolve the tmux target from persisted runtime session state / `agent_identity`, so callers do not need to manually discover window names.
3. Support a clear first-class key vocabulary for at least:
   - `Escape`
   - `Up`
   - `Down`
   - `Left`
   - `Right`
   - `Enter`
   - `Tab`
4. Support sending short key sequences, not only single keys, so callers can drive menus predictably.
5. Expose this through a caller-facing runtime surface, for example a CLI command and backend/session-control method, rather than requiring ad-hoc tmux subprocess calls in external scripts.
6. Define behavior and errors when the session is not tmux-backed, the tmux window cannot be resolved, or the target key is unsupported.

## Acceptance Criteria
1. A CAO-backed session resumed by `agent_identity` can receive tmux-delivered special keys without manual `tmux send-keys` shell work by the caller.
2. A caller can drive an interactive provider menu such as `/model` using runtime-supported key input and then continue normal `send-prompt` turns in the same session.
3. Runtime session resolution remains manifest-driven and does not require the caller to know raw tmux window ids/names.
4. Errors are explicit for unsupported backends, missing tmux targets, and unsupported key names.
5. Tests cover at least:
   - successful `Escape` delivery,
   - successful arrow-key navigation input,
   - failure on unresolved tmux target,
   - failure on non-tmux-backed session.
6. Developer/operator docs explain when to use prompt submission vs tmux key input.

## Non-Goals
- No requirement to route special keys through CAO inbox messaging.
- No requirement to support arbitrary raw binary input as the first step.
- No requirement to redesign the shadow parser contract itself.
- No requirement to make every provider menu automatable; the initial goal is to expose the key-input primitive cleanly.

## Suggested Follow-Up
- Create an OpenSpec change for runtime control-input support on tmux-backed CAO sessions.
- Decide whether the same tmux `send-keys` mechanism should also be exposed for non-CAO tmux-backed headless sessions (`claude_headless`, `codex_headless`, `gemini_headless`) or remain CAO-scoped initially.
- Add a small demo or regression test that drives a slash menu with arrow keys and then resumes normal turn submission.
