## Context

`houmao-touring` is a manual guided-tour skill that orients users on current Houmao state and then routes them into narrower Houmao-owned skills for execution. It currently covers setup, mailbox, specialist/profile authoring, launch, live operations, reminders, and lifecycle follow-up.

The packaged loop skills are already installed through the user-control set. `houmao-agent-loop-pairwise` is the restored stable pairwise planner and run controller, while `houmao-agent-loop-pairwise-v2` is the enriched versioned pairwise workflow with prestart initialization and expanded run-control actions. Both pairwise skills intentionally remain manual-invocation-only and warn against auto-routing generic pairwise loop requests into them.

The touring skill needs to make this advanced path discoverable without becoming another loop-planning skill and without restating the elemental pairwise edge protocol from `houmao-adv-usage-pattern`.

## Goals / Non-Goals

**Goals:**

- Add an advanced-usage branch to the touring skill.
- Make pairwise agent-loop creation discoverable from a guided tour.
- Distinguish the stable pairwise skill from the v2 pairwise skill in plain tour-oriented language.
- Preserve the explicit-selection/manual-invocation boundary for the pairwise skills.
- Route composed pairwise loop planning and run-control details to `houmao-agent-loop-pairwise` or `houmao-agent-loop-pairwise-v2`.
- Keep elemental edge protocol details on `houmao-adv-usage-pattern`.

**Non-Goals:**

- Do not change the pairwise loop skills' own behavior or lifecycle vocabulary.
- Do not add a runtime loop engine, CLI command, graph helper, or mailbox/gateway behavior.
- Do not make `houmao-touring` the default entrypoint for ordinary pairwise loop planning requests outside the guided-tour context.
- Do not restate full pairwise edge-loop mailbox/reminder protocols inside touring.

## Decisions

### Decision: Add a dedicated touring branch page

Add `branches/advanced-usage.md` instead of expanding the top-level `SKILL.md` with all branch detail. The top-level skill should remain an index/router, while the branch page owns tour-friendly descriptions, branch choices, and guardrails for advanced loop creation.

Alternative considered: only add a paragraph to `SKILL.md`. Rejected because the touring skill already keeps branch-specific workflow under `branches/`, and advanced loop selection has enough boundary nuance to deserve a branch page.

### Decision: Present pairwise skills as explicit choices, not automatic routing

The advanced branch should explain that selecting the stable pairwise path means invoking `houmao-agent-loop-pairwise`, and selecting the enriched path means invoking `houmao-agent-loop-pairwise-v2`. This preserves the pairwise skills' manual-invocation posture while still making the options discoverable during a tour.

Alternative considered: make the tour silently route any loop-creation intent to v2. Rejected because both pairwise skills explicitly prohibit auto-routing generic pairwise loop requests, and the stable/v2 distinction is an operator-facing choice.

### Decision: Keep touring at the selection/orientation layer

The advanced branch should describe the key decision points: stable versus enriched pairwise, user agent outside the execution loop, master-owned supervision, and elemental edge protocol ownership. It should not copy plan templates, run charters, stop modes, routing packets, or the full mailbox/reminder protocol.

Alternative considered: embed a compact pairwise plan template in touring. Rejected because that would duplicate the pairwise skills and make future pairwise workflow changes harder to keep consistent.

## Risks / Trade-offs

- [Risk] Touring could accidentally undermine the manual-invocation boundary by saying it "routes" straight into pairwise skills. -> Mitigation: phrase the branch as presenting explicit choices and instructing the user or calling agent to invoke the selected pairwise skill by name.
- [Risk] Users may not understand when to pick stable versus v2. -> Mitigation: describe stable as the simpler `plan/start/status/stop` path and v2 as the enriched `plan/initialize/start/peek/ping/pause/resume/stop/hard-kill` path.
- [Risk] Touring could drift into protocol duplication. -> Mitigation: add guardrails that composed topology stays with pairwise loop skills and elemental edge protocol stays with `houmao-adv-usage-pattern`.

## Migration Plan

No data migration is required. The change only updates packaged system-skill assets and projection tests. Rollback is to remove the touring advanced branch references and the new branch page.

## Open Questions

- Should a future change add a broader advanced-usage branch that also introduces `houmao-agent-loop-generic`, or should this change stay focused on the requested pairwise loop creation path?
