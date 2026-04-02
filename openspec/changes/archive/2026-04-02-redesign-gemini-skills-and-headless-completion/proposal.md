## Why

Gemini mailbox wake-up flows currently rely on an awkward split between where Houmao installs Gemini-owned mailbox skills and which skill paths prompts tell the agent to open from the working directory. That split leaks implementation details into prompts, makes demo and runtime behavior diverge, and encourages path-based skill usage instead of native Gemini skill invocation.

Tmux-backed headless completion also mixes transient live detail with durable process artifacts. In practice this makes successful one-off headless turns look active or incomplete until later inspection catches up, which weakens managed-agent detail semantics and makes verification flows race-prone.

## What Changes

- Redesign Gemini mailbox system-skill projection so Houmao-owned Gemini mailbox skills install as native top-level skills under `.agents/skills/` without the extra `mailbox/` subtree.
- Redesign Gemini notifier and mailbox prompts to invoke Houmao-owned Gemini mailbox skills by skill name rather than by file path.
- Define tmux-backed native headless turn completion around the managed child process reaching terminal exit and the corresponding durable exit artifact being written.
- Reconcile managed-agent headless detail and demo verification from durable terminal turn evidence instead of stale transient live detail when those disagree.
- Update the single-agent gateway wake-up headless demo to exercise the native Gemini skill contract and the process-exit completion contract.
- **BREAKING**: Change the Gemini mailbox skill naming and projection contract from `.agents/skills/mailbox/houmao-...` path-oriented usage to top-level `.agents/skills/houmao-...` native skill usage.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `agent-mailbox-system-skills`: Gemini mailbox skills change from namespaced path-oriented documents to native top-level installed Houmao skills invoked by name.
- `brain-launch-runtime`: tmux-backed native headless turn completion becomes process-exit-driven with durable exit artifacts as the authoritative terminal evidence.
- `managed-agent-detailed-state`: headless detail reconciles last-turn status and prompt-readiness from durable terminal turn evidence rather than transient tmux/live posture alone.
- `single-agent-gateway-wakeup-headless-demo`: the maintained demo verifies Gemini wake-up behavior against native Gemini skill invocation and process-exit headless completion.

## Impact

- Affected code includes mailbox skill projection helpers, Gemini runtime/build adapters, gateway notifier prompt construction, headless runtime completion tracking, managed-agent detail reporting, and the single-agent gateway wake-up headless demo harness.
- Affected tests include Gemini mailbox skill projection tests, gateway prompt tests, managed-agent headless detail tests, and demo verification tests.
- Affected docs include mailbox skill contracts, Gemini backend/runtime references, and demo/operator guidance.
