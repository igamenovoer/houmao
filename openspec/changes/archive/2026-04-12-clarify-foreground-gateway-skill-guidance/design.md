## Context

Houmao currently supports two live gateway execution postures for tmux-backed managed sessions: same-session auxiliary tmux window execution and detached background process execution. The CLI already treats foreground auxiliary-window execution as the normal attach path for `agents gateway attach`; easy-instance launch also auto-attaches a gateway by default and only requests detached execution through an explicit background flag.

The gap is in packaged system-skill guidance. `houmao-agent-gateway` documents a background attach example but does not strongly state that background mode requires explicit user intent. `houmao-specialist-mgr`, `houmao-agent-instance`, and `houmao-touring` route launch flows that can create or observe gateway-backed sessions, but their guidance leaves the posture easy to infer incorrectly. One advanced-usage composition page also points agents at gateway attach and should inherit the same posture rule.

## Goals / Non-Goals

**Goals:**

- Make foreground same-session tmux gateway execution the explicitly taught first choice for skills that launch or attach gateways.
- Require explicit user intent before an agent adds `--background` or `--gateway-background`.
- Preserve existing user-controlled ways to request background gateway execution.
- Help guided tours explain the observable tmux topology: agent surface on window `0`, gateway in a non-zero auxiliary window when foreground gateway execution is active.
- Distinguish gateway background execution from the CLI's non-interactive tmux handoff behavior, where a session may be left detached but the gateway can still be foreground auxiliary-window backed.

**Non-Goals:**

- Do not change `houmao-mgr` CLI defaults, runtime gateway execution behavior, or status payload schemas.
- Do not remove `--background` or `--gateway-background`.
- Do not make every route-only mention of gateway attach restate the full posture contract.
- Do not add new gateway lifecycle commands or profile fields.

## Decisions

1. Keep the canonical rule on `houmao-agent-gateway` and make other skills point at or mirror that rule only where they teach launch or attach.

   Alternative considered: duplicate the same long explanation across every skill that mentions gateways. That would drift quickly. The better approach is for `houmao-agent-gateway/actions/lifecycle.md` to carry the detailed attach rule, while launch-owning skills add concise foreground-first notes where agents choose launch flags.

2. Treat explicit user intent as the only reason for skills to add background gateway flags.

   The skill text should recognize intent phrased as "background", "detached gateway process", or "do not add a tmux gateway window". Absent that wording, agents should prefer the command without `--background` or `--gateway-background`. This keeps the current CLI capability available without letting agents choose the less observable posture on their own.

3. Teach launch-time gateway posture separately from managed-agent headless posture.

   `--headless` controls the provider/session launch posture, while `--gateway-background` controls the gateway sidecar execution mode. The guidance should avoid implying that a headless managed agent requires a background gateway. For Gemini, headless launch remains required by existing constraints, but that does not by itself authorize detached gateway execution.

4. Make touring explicit about tmux handoff semantics.

   Tours often run from an agent or automation context without an interactive terminal. The command may therefore print an attach command instead of switching the operator into tmux. That is not the same as background gateway execution. The tour guidance should tell agents to report the attach command and gateway execution metadata instead of "fixing" that by adding background flags.

5. Use system-skill content tests as the primary regression guard.

   This change is documentation and packaged skill content. Targeted tests should assert that the installed skill text contains the foreground-first and explicit-background rules in the direct teaching surfaces, rather than adding runtime gateway tests for behavior that already exists.

## Risks / Trade-offs

- Some skill pages may become repetitive -> keep detailed topology language in `houmao-agent-gateway` and use shorter cross-references elsewhere.
- Agents may over-ask when a user says "background" indirectly -> document acceptable intent phrases and keep the rule focused on launch/attach flag selection.
- Existing tests may not cover every installed page -> add targeted assertions for direct command-teaching pages and rely on an `rg` audit for route-only mentions.
