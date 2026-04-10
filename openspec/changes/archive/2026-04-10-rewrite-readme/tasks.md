## 1. Condense the intro

- [x] 1.1 Replace the four intro subsections (What It Is, Core Idea, What The Framework Provides, Why This Is Useful) with two: **What It Is** (one paragraph) and **Why This Approach** (bullet list). Preserve the name-origin blockquote. Drop the "What We Avoid" framing.

## 2. Rewrite Quick Start sections

- [x] 2.1 Write step 0 — Install & Prerequisites: `uv tool install houmao`, tmux check, `houmao-mgr system-skills install --tool claude --home ~/.claude` with explanation. Add skip-note for join-only users.
- [x] 2.2 Write step 1 — Initialize a Project: `houmao-mgr project init`, brief `.houmao/` overlay explanation.
- [x] 2.3 Write step 2 — Create Specialists & Launch Agents: full `easy specialist create` command, `easy instance launch`, management commands (`agents prompt`, `agents stop`), mention easy profiles.
- [x] 2.4 Write step 3 — Agent Loop: Multi-Agent Coordination. Reference the stable `houmao-agent-loop-pairwise` skill (not v2). Include: pairwise loop explanation (master owns liveness, user stays outside), agentsys2 specialist creation commands (story-writer/claude, character-designer/claude, story-reviewer/codex) and instance launch commands, a loop plan adapted to the stable skill's single-file template (Objective, Master, Participants, Delegation Policy, Completion Condition, Stop Policy, Reporting Contract, Mermaid Control Graph), the lifecycle (plan → start → status → stop via the skill), produced artifact listing from the actual run (5 chapters, 5 character profiles, 4 review reports), skill reference, non-coding context note.
- [x] 2.5 Move existing `agents join` content to step 4 — reframe as lightweight/ad-hoc path ("if you already have a coding agent running"). Keep the mermaid diagram and capabilities table.
- [x] 2.6 Move existing Full Recipes and Launch Profiles content to step 5 — keep mostly as-is.

## 3. Revise Typical Use Cases

- [x] 3.1 Revise the Typical Use Cases list to lead with specialist-based and loop-based examples. Keep parallel-specialist and swap-the-AI cases.

## 4. Reorder remaining sections

- [x] 4.1 Reorder the remaining sections to match the design: System Skills, Subsystems at a Glance, Runnable Demos, CLI Entry Points, Full Documentation, Development. Keep their content as-is. Move CLI Entry Points table below Runnable Demos.

## 5. Verify

- [x] 5.1 Review the final README for internal consistency: all section cross-references still valid, no broken links, mermaid renders, no duplicate content from the move.
