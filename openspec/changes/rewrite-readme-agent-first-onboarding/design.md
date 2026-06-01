## Context

The README already introduces Houmao as a system for real CLI agents with isolated state, gateways, mailbox messaging, specialists, and loops. The problem begins in the Quick Start and usage material: the document shifts into a long manual `houmao-mgr` tutorial and full skill catalog, which makes the human operator look responsible for memorizing command surfaces that Houmao system skills are designed to drive from inside a CLI agent.

The desired README posture is closer to the OpenSpec README style: show a short install, then show "You ask / AI does" interaction examples. Command syntax should remain discoverable, but the README should treat it as machinery behind the agent-driven experience and link to docs for details.

## Goals / Non-Goals

**Goals:**

- Make the README's first runnable path: install Houmao, verify `tmux`, install skills, start a CLI agent, invoke `houmao-touring`.
- Prefer `npx skills add igamenovoer/tool-skills/houmao` for ordinary skill installation and still mention `houmao-mgr system-skills install ...` for offline/custom installs.
- Explain specialists, easy profiles, managed agents, gateways, and mailbox interaction through conversation-shaped examples.
- Present `houmao-agent-loop-pro` as the strongest Houmao story for complex multi-agent plans.
- Keep README concise and route detailed command flags, full skill catalog material, and lower-level adoption or recipe paths to docs.

**Non-Goals:**

- No runtime behavior, CLI command, system skill, or packaging changes.
- No new documentation site page unless an implementation pass finds an existing docs link missing.
- No exhaustive reference coverage in README.

## Decisions

1. **Make the CLI agent the main actor.**
   - Decision: The README SHALL describe the user driving Houmao through a CLI agent with Houmao skills.
   - Rationale: This matches the product advantage and reduces the apparent learning burden.
   - Alternative considered: Keep the current command-first Quick Start and add an agent-driven note. That keeps the old failure mode: the reader still sees command memorization first.

2. **Use a short install block followed by tour activation.**
   - Decision: The Quick Start SHALL show `uv tool install houmao`, `command -v tmux`, `npx skills add igamenovoer/tool-skills/houmao`, then a prompt to invoke `houmao-touring`.
   - Rationale: This creates a small, memorable first path and follows the user's preferred install ordering.
   - Alternative considered: Lead with `houmao-mgr system-skills install`. That remains supported, but it is better framed as fallback/custom tooling.

3. **Use conversation examples instead of long command recipes.**
   - Decision: Usage examples SHALL use "You:" and "AI:" blocks to show specialist creation, easy profile preparation, launch, gateway interaction, and loop operation.
   - Rationale: The README should teach the mental model and payoff, while docs own command shape.
   - Alternative considered: Preserve full CLI equivalents under every example. That makes the README too long and blurs the user/agent boundary.

4. **Elevate pro loops over command-level loop lifecycle.**
   - Decision: The loop section SHALL describe feeding a complex multi-agent plan to `houmao-agent-loop-pro`, letting the agent decompose and prepare the run, and then observing/controling the loop from outside.
   - Rationale: This is Houmao's most distinctive multi-agent value and better than presenting loop subcommands as the main artifact.
   - Alternative considered: Keep the story-writing loop as a command-heavy tutorial. It can remain linked as an example, but should not dominate the README usage path.

5. **Compress reference material into docs links.**
   - Decision: The README SHALL summarize system skills and CLI entry points, not list every skill or flag.
   - Rationale: Detailed surfaces already belong in getting-started and reference docs, and the README's job is conversion and orientation.
   - Alternative considered: Keep the full catalog for discoverability. That improves completeness but weakens first-read clarity.

## Risks / Trade-offs

- **Risk: Readers who prefer manual CLI examples may feel under-served.** → Mitigation: Keep explicit links to the getting-started guides and CLI reference near each compact example.
- **Risk: Tests or specs currently assert old Quick Start headings and snippets.** → Mitigation: Update README-structure tests and docs guards alongside the rewrite.
- **Risk: Over-compressing system skills may hide important capabilities.** → Mitigation: Mention the major skill families and link to the System Skills Overview for the full catalog.
- **Risk: The README could imply the user never needs CLI commands.** → Mitigation: Phrase commands as supported machinery that the user's CLI agent usually operates, with docs available for direct/manual use.
