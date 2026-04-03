## Context

Houmao already projects runtime-owned mailbox skills into tool-native runtime homes during brain build. Claude, Codex, and Gemini each have a maintained runtime-home skill destination, and supported prompt surfaces are supposed to rely on those installed skills rather than on copied project content.

The current mismatch comes from three layers above the runtime projection:

- supported and archived demos still copy mailbox skills into the copied project worktree or verify success through that mirror,
- some archived prompts still tell agents to open `skills/.../SKILL.md` from the worktree,
- reference docs still describe notifier skill guidance as installed-path substitution rather than native invocation guidance.

Because the runtime projection layer is already correct, this change should remove the contract violations around it instead of redesigning mailbox skill installation itself.

## Goals / Non-Goals

**Goals:**
- Make supported mailbox wake-up flows depend only on runtime-home mailbox skill installation.
- Remove project-workdir mailbox skill mirrors from maintained demos.
- Require agent-facing notifier guidance to use native mailbox-skill invocation rather than `SKILL.md` paths.
- Block archived legacy demos that still depend on the deprecated mirror/path contract and explain why they are not runnable.
- Align docs and demo verification with the runtime-home mailbox-skill contract.

**Non-Goals:**
- Rework the mailbox skill asset set or rename Houmao mailbox skills.
- Change the underlying runtime-home installation layout for Claude, Codex, or Gemini.
- Repair archived legacy demos so they run under the new contract.
- Introduce a generic migration framework for arbitrary archived demos.

## Decisions

### Decision: Treat runtime-home mailbox skills as the only maintained mailbox-skill surface

Supported demos and prompts will use the installed runtime-home skill surface as the single source of truth. Copied project worktrees may still contain ordinary project files, but they will not receive mirrored Houmao runtime-owned mailbox skills.

Why:
- It matches the existing brain-build contract.
- It prevents supported demos from succeeding for the wrong reason.
- It keeps agent prompting aligned with actual provider-native skill discovery.

Alternative considered:
- Keep project mirrors as a compatibility fallback while “preferring” runtime-home skills.
- Rejected because the fallback continues to hide regressions and preserves the invalid contract in maintained flows.

### Decision: Encode native mailbox-skill prompting at the prompt-construction layer, not in per-demo ad hoc text

Gateway notifier prompts and other mailbox wake-up prompt surfaces will express mailbox skill usage in native tool terms:

- Claude: installed skill by native skill invocation/name
- Codex: installed skill by native `$skill-name` trigger form when explicit invocation is needed
- Gemini: installed skill by name

Prompt text will explicitly avoid `skills/.../SKILL.md` references for ordinary runtime prompting.

Why:
- The prompt layer is where provider-specific invocation syntax matters.
- Runtime-home installation alone is not enough if the wake-up prompt still teaches a path/document workflow.

Alternative considered:
- Keep generic “use this skill by name” wording for every provider.
- Rejected because Codex in particular benefits from an explicit native trigger contract.

### Decision: Fail fast in archived legacy demo entry points instead of partially modernizing them

Archived legacy demos that still rely on project-local mailbox skill mirrors or path-based skill prompting will stop at entry and print a clear explanation that they are archived because they depend on a deprecated mailbox-skill contract.

Why:
- The user explicitly does not want time spent repairing legacy demos.
- A fail-fast guard is safer than leaving known-invalid workflows runnable.

Alternative considered:
- Quietly leave archived demos broken and rely on docs to discourage use.
- Rejected because operators can still reach those entry points directly and waste time on invalid workflows.

### Decision: Update verification to prove runtime-home skill availability instead of mirrored-project availability

Supported demo reporting will verify the installed runtime-home mailbox skill surface and, where relevant, explicitly record that no project-local mirror is present.

Why:
- Verification should prove the maintained contract, not the deprecated workaround.
- This keeps future regressions visible during demo testing.

Alternative considered:
- Remove all skill-surface verification from demos.
- Rejected because the native-skill contract is a critical part of what these demos are supposed to exercise.

## Risks / Trade-offs

- [Archived demo callers may be surprised by fail-fast behavior] → Return a precise error that names the deprecated project-skill mirror/path contract and points callers back to maintained demos.
- [Provider-native invocation wording may drift from upstream behavior] → Keep the contract centralized in mailbox/notifier prompt construction and verify with targeted prompt tests and live demo runs.
- [Docs may still imply project-local skill behavior through legacy terminology] → Update the affected reference pages in the same change and align demo/report wording with runtime-home terminology.
- [Current doc names such as “project mailbox skills” can still sound misleading] → Clarify the page content now; defer file renames unless they become necessary in a later docs-only cleanup.

## Migration Plan

1. Update maintained mailbox demo/reporting surfaces to remove project-local mailbox-skill mirrors and verify runtime-home installation instead.
2. Update gateway notifier prompting and related docs to describe native mailbox-skill invocation without `SKILL.md` paths.
3. Add fail-fast guards to archived legacy demo entry points that still rely on the deprecated contract.
4. Run targeted unit tests and live demo verification for supported Claude/Codex lanes.

Rollback is straightforward: revert the maintained demo/reporting and legacy entry-point guard changes together. No persisted data migration is involved.

## Open Questions

- Should the documentation page currently named `project-mailbox-skills` be renamed later to better reflect runtime-home rather than project-content behavior? This change will clarify the content but not rename the page unless implementation work shows that the current name is actively causing confusion beyond wording fixes.
