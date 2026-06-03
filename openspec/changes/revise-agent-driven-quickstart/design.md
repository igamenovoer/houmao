## Context

`docs/getting-started/quickstart.md` currently opens as a from-source command walkthrough. It lists `agents self join` first, then walks through `project init`, skill registration, specialist creation, direct native-agent inspection, manual brain build, managed launch, prompt, stop, and optional mailbox setup. That content is useful reference material, but it does not match the current product story in `README.md` and `docs/getting-started/system-skills-overview.md`: the normal first-run experience is conversational agent control through installed Houmao system skills.

The intended reader is a user with Claude Code, Codex, Gemini, or another compatible CLI-agent surface. They want to make Houmao useful from inside their current agent session, not learn every `houmao-mgr` command before they see the workflow.

## Goals / Non-Goals

**Goals:**

- Make the quickstart's first path agent-driven: install Houmao, install system skills, start the user's CLI agent in the project, invoke `houmao-touring`, then ask for a first managed-agent outcome.
- Keep command examples accurate, but make them the agent's underlying machinery or a manual fallback.
- Preserve useful from-source guidance through a launcher note that maps installed-user commands to `pixi run houmao-mgr ...` for source checkouts.
- Preserve `agents self join` as an adoption workflow for an already-running provider TUI, but stop presenting it as the primary first-run path.
- Keep cross-links to System Skills Overview, Easy Specialists, Launch Profiles, gateway, mailbox, memory, and CLI reference pages.

**Non-Goals:**

- Do not change CLI behavior, skill behavior, runtime lifecycle, or system-skill catalog membership.
- Do not add a new docs page unless implementation reveals that the quickstart becomes too long.
- Do not convert the quickstart into a full CLI reference; the dedicated reference pages remain authoritative for flags and edge cases.

## Decisions

### Lead with the user-agent mental model

The quickstart should name the actor split early:

```text
user -> user CLI agent -> Houmao system skills -> houmao-mgr -> managed agents
```

Rationale: the first conceptual hurdle is not a command flag. It is the difference between the agent the user is currently talking to and the managed agents Houmao creates, adopts, prompts, and inspects.

Alternative considered: keep the current two workflows and add a short note that agents can run the commands. That would preserve the current shape, but it would still make manual command execution look like the recommended first experience.

### Use a first useful prompt instead of a long command script

The first end-to-end example should be a `You:` / `AI:` style request, such as creating a reviewer specialist, preparing a profile, launching a managed agent, prompting it, inspecting state, and stopping it. The surrounding prose should explain what the agent is expected to do, what state appears under `.houmao/`, and what durable concepts the user now owns.

Rationale: the README already uses this agent-mediated example style, and the quickstart should deepen it rather than contradict it.

Alternative considered: provide only `$houmao-touring` and delegate all other learning to the tour. That would be too thin for a getting-started page because readers still need a durable written model and direct links.

### Keep direct commands as transparent machinery

Manual commands should remain visible in a compact section titled as fallback, debugging, or "what the agent may run." That section can reuse the current maintained commands, but it should not require the reader to manually type every step before understanding Houmao's value.

Rationale: Houmao is still a CLI toolkit, and source developers need exact commands. The docs should expose those commands without making them the default user journey.

Alternative considered: remove most commands from quickstart and link only to CLI reference. That would make the quickstart friendlier, but it would hurt developers and users who need to debug the agent-driven path.

### Treat join as adoption, not first-run setup

`agents self join` should remain in the quickstart because it is a supported local entry point. The revised page should frame it as "when you already have a provider TUI running" and keep the Mermaid adoption diagram.

Rationale: join is valuable, but the product's first-run story now centers on the user's CLI agent asking Houmao skills to create and operate managed agents.

Alternative considered: move join out of the quickstart. That would reduce page length, but it would hide a common repair and adoption path that belongs in getting-started material.

## Risks / Trade-offs

- Readers who prefer shell commands may feel the quickstart is less concrete. Mitigation: keep a manual fallback section and link to CLI reference.
- The page may duplicate README wording. Mitigation: use README as the 60-second summary and make quickstart the hands-on agent-driven guide with more state and fallback detail.
- Agent-facing prompts can age as skills evolve. Mitigation: keep prompts outcome-oriented and avoid baking in exact internal routing unless the docs intentionally show underlying machinery.
