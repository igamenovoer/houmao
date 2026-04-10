## Context

The current README (281 lines) has four intro subsections, leads with `agents join` as the recommended path, and has no coverage of agent loops. The agentsys2 project provides a real worked example of the pairwise loop: 3 specialists (story-writer/claude, character-designer/claude, story-reviewer/codex) coordinating through a per-chapter pipeline that produced 5 chapters, 5 character profiles, and 4 review reports.

The README is the repo landing page (not part of the mkdocs site), so it serves both GitHub visitors and `uv tool install` users landing on the project for the first time.

## Goals / Non-Goals

**Goals:**

- Make the specialist → profile → launch path the obvious primary workflow
- Position `system-skills install` as a visible prerequisite (step 0)
- Introduce `project init` and the `.houmao/` overlay early so users understand the project scaffold
- Add an agent loop section with the agentsys2 story-writing example showing specialist creation commands, loop plan structure, mermaid control graph, and produced artifacts
- Keep `agents join` documented but as a secondary "lightweight / ad-hoc" path
- Condense the intro from 4 subsections to 2
- Keep the README self-contained enough to get started without visiting the docs site

**Non-Goals:**

- Rewriting the docs site guides (easy-specialists.md, launch-profiles.md, etc.)
- Changing any CLI behavior or system skill content
- Adding new runnable demo scripts
- Covering relay loops (pairwise loop is enough for the README showcase)

## Decisions

### D1: Section ordering

New order:

1. **Houmao** (title + tagline + name origin) — keep as-is
2. **What It Is** — condensed from 4 subsections into ~2 paragraphs: what it does, why this approach
3. **Quick Start** — the numbered walkthrough:
   - 0. Install & Prerequisites (uv install, tmux, `system-skills install`)
   - 1. Initialize a Project (`project init`, explain `.houmao/`)
   - 2. Create Specialists & Launch Agents (primary path — `easy specialist create`, `easy instance launch`, management commands, mention easy profiles)
   - 3. Agent Loop: Multi-Agent Coordination (agentsys2 showcase)
   - 4. Adopt an Existing Session (`agents join` — lightweight path)
   - 5. Full Recipes and Launch Profiles (advanced)
4. **Typical Use Cases** — revised to lead with specialist/loop examples
5. **System Skills** — keep existing table
6. **Subsystems at a Glance** — keep as-is
7. **Runnable Demos** — keep as-is
8. **CLI Entry Points** — keep as-is
9. **Full Documentation + Development** — keep as-is

**Rationale:** The numbered steps mirror the actual onboarding sequence. System-skills install comes first because without it agents cannot self-manage. Project init comes before specialist creation because specialists live under `.houmao/`. The loop section follows specialist creation because it requires multiple specialists already set up.

### D2: Agent loop section content

The agentsys2 example was driven by the stable `houmao-agent-loop-pairwise` skill (the current version in `src/houmao/agents/assets/system_skills/houmao-agent-loop-pairwise/`), which provides the simpler plan + `start|status|stop` lifecycle. The catalog also ships `houmao-agent-loop-pairwise-v2` (enriched, with `initialize|peek|ping|pause|resume|hard-kill`), but the README showcase should reference only the stable skill since that's what the example actually used.

Include in the README:
- Brief explanation of what a pairwise loop is (master drives edges to workers, user stays outside the execution loop; after master accepts, master owns liveness)
- The agentsys2 example setup:
  - `houmao-mgr project init`
  - `houmao-mgr system-skills install --tool claude --home ~/.claude` (if not already done)
  - `houmao-mgr project easy specialist create` commands for all 3 specialists (story-writer/claude, character-designer/claude, story-reviewer/codex)
  - `houmao-mgr project easy instance launch` for each specialist
- The loop plan: show the single-file plan template fields (Objective, Master, Participants, Delegation Policy, Completion Condition, Stop Policy, Reporting Contract, Mermaid Control Graph) with the story-chapter-loop content adapted to the stable skill's conventions
- The mermaid control graph showing: User Agent (control only) → Master (alex-story) → Workers (alex-char, alex-review), with the per-chapter supervision loop
- The lifecycle: user agent invokes the `houmao-agent-loop-pairwise` skill to plan → start → status → stop
- A summary of produced artifacts from the actual run: 5 chapters, 5 character profiles, 4 review reports — listed as paths, not file contents
- Reference to the `houmao-agent-loop-pairwise` skill and the system-skills overview guide for the full vocabulary

**Rationale:** Shows enough to understand the capability and reproduce it, without turning the README into a tutorial. The mermaid graph is the single most informative visual. Using the stable skill (not v2) keeps the example aligned with what the reader will get by default.

### D3: Intro condensation

Merge the current four subsections:
- "What It Is" + "The Core Idea" → **What It Is** (one paragraph: what Houmao does, each agent is a real CLI process)
- "What The Framework Provides" + "Why This Is Useful" → **Why This Approach** (bullet list, rewritten to lead with specialist/project/loop capabilities, join mentioned as one bullet)

Drop the "What We Avoid" framing (too defensive for a README intro). Keep the name-origin blockquote.

### D4: system-skills install positioning

Place as step 0 in Quick Start with this framing: "Install system skills into your agent's tool home so it can self-manage Houmao workflows through its native skill interface." Show the command for claude, mention codex/gemini variants.

**Alternative considered:** Keep it as a footnote. Rejected because without system skills the agent cannot drive any Houmao workflow autonomously — it's a hard prerequisite for the recommended path.

### D5: What to keep verbatim

- The name-origin blockquote
- The `agents join` mermaid sequence diagram (move it into the section 4 position)
- The "What You Get After Joining" capabilities table
- The system skills table
- The subsystems table
- The runnable demos section
- The CLI entry points table
- The development commands block

## Risks / Trade-offs

- [README length may increase] → The agent loop section adds ~60-80 lines. Offset by condensing the intro (~40 lines saved). Net increase ~20-40 lines, acceptable for a project README.
- [agentsys2 example may feel detached from a code-project context] → The story-writing example is intentionally non-code to show Houmao isn't just for coding agents. Add a one-line note: "This example uses creative-writing specialists; the same pattern works for code review, optimization, or any multi-agent pipeline."
- [system-skills install as step 0 may confuse users who just want to try `agents join`] → Add a note: "If you just want to try `agents join` without project setup, skip to section 4. System skills are recommended but not required for the join path."
