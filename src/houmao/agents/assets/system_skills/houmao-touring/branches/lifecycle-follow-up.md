# Lifecycle Follow-Up Branch

Use this branch when the user wants to inspect, stop, relaunch, or clean up managed-agent sessions.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. If the user is unsure which agent exists, route discovery to `houmao-agent-instance` and list current managed agents first.
3. Explain the lifecycle choices in plain language before routing:
   - `stop` ends the live managed-agent session
   - `relaunch` restarts a relaunchable managed session without treating it as a fresh launch
   - `cleanup` removes artifacts for a stopped session and still requires a cleanup kind such as `session` or `logs`
4. Route the selected lifecycle action to `houmao-agent-instance`.
5. After the lifecycle action completes, summarize the current posture and offer the next likely branches:
   - relaunch or re-open live operations if the agent is still available
   - launch another agent
   - create another specialist
   - clean up stopped-session artifacts when appropriate

## Guardrails

- Do not collapse stop, relaunch, and cleanup into one action.
- Do not reinterpret relaunch as a fresh launch when relaunch is unavailable.
- Do not present cleanup as safe for a live session or as an automatic next step after stop.
