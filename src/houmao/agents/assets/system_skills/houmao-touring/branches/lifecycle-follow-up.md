# Lifecycle Follow-Up Branch

Use this intermediate branch when the user wants to inspect, stop, relaunch, join/adopt, or clean up managed-agent sessions.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. If the user is unsure which agent exists, route discovery to `houmao-agent-inspect` and inspect current managed agents first.
3. Explain the lifecycle choices in plain language before routing:
   - `inspect` reads the current managed-agent state, screen posture, mailbox posture, logs, or runtime artifacts without mutating the session
   - `stop` ends the live managed-agent session
   - `relaunch` restarts a relaunchable managed session without treating it as a fresh launch
   - `join/adopt` brings an existing compatible session under managed lifecycle when the user explicitly asks for that posture
   - `cleanup` removes artifacts for a stopped session and still requires a cleanup kind such as `session` or `logs`
4. Route `inspect` to `houmao-agent-inspect`, and route `stop`, `relaunch`, `join/adopt`, or `cleanup` to `houmao-agent-instance`.
5. After the lifecycle action completes, summarize the current posture and offer stage-aware next actions:
   - relaunch or re-open live operations if the agent is still available
   - launch another agent
   - create another specialist
   - inspect logs, turn evidence, mailbox posture, or runtime artifacts
   - return to memo, mailbox, gateway, reminder, or manual coordination work when an agent is running
   - move to advanced loop or isolated workspace guidance only when team coordination or workspace isolation is the user's goal
   - clean up stopped-session artifacts when appropriate

## Guardrails

- Do not collapse stop, relaunch, and cleanup into one action.
- Do not reinterpret relaunch as a fresh launch when relaunch is unavailable.
- Do not present cleanup as safe for a live session or as an automatic next step after stop.
- Do not treat join/adopt as a beginner requirement; use it only when the user asks to bring an existing session under management.
