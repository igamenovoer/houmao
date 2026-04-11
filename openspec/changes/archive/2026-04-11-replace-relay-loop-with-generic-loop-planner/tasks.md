## 1. Asset Rename And Skill Boundary

- [x] 1.1 Rename `src/houmao/agents/assets/system_skills/houmao-agent-loop-relay/` to `src/houmao/agents/assets/system_skills/houmao-agent-loop-generic/`.
- [x] 1.2 Update the top-level `SKILL.md` metadata and overview so the skill name, description, scope, routing guidance, and guardrails describe generic loop graph planning rather than relay-only planning.
- [x] 1.3 Update `agents/openai.yaml` so the default prompt invokes `$houmao-agent-loop-generic` and describes typed pairwise/relay graph decomposition.
- [x] 1.4 Remove current-source references that present `houmao-agent-loop-relay` as a current packaged skill rather than the retired name.

## 2. Generic Planning Content

- [x] 2.1 Rewrite `authoring/formulate-loop-plan.md` to classify user intent into typed loop components and require `component_type: pairwise|relay` per component.
- [x] 2.2 Rewrite `authoring/revise-loop-plan.md` to preserve typed component boundaries and revalidate pairwise local-close versus relay egress-return semantics after revisions.
- [x] 2.3 Rewrite `authoring/render-loop-graph.md` to render mixed typed components, component dependencies, pairwise local-close returns, relay egress returns, supervision, completion, and stop.
- [x] 2.4 Replace relay-only route guidance with generic graph/component policy guidance covering pairwise delegation policy and relay route policy.
- [x] 2.5 Rewrite result-routing guidance so pairwise components return to the immediate driver and relay components return from egress to relay origin.
- [x] 2.6 Rewrite plan-structure and template files so plans contain loop components, graph policy, result routing, typed component graph, and Mermaid generic loop graph sections rather than relay-only lanes.
- [x] 2.7 Rewrite run-charter guidance so `start` passes a typed component plan summary to the root owner and routes component execution to the elemental advanced-usage protocols.

## 3. Operating Lane

- [x] 3.1 Update `operating/start.md` so accepted generic runs transfer liveness to the root owner and dispatch pairwise or relay components through their elemental protocols.
- [x] 3.2 Update `operating/status.md` so status reports typed component posture, active pairwise components, active relay components, blockers, completion posture, and stop posture without becoming a keepalive.
- [x] 3.3 Update `operating/stop.md` so stop handling applies to the generic component graph while preserving interrupt-first default and explicit graceful-stop handling.

## 4. Catalog And Documentation

- [x] 4.1 Update `src/houmao/agents/assets/system_skills/catalog.toml` to replace the `houmao-agent-loop-relay` skill entry and `user-control` member with `houmao-agent-loop-generic`.
- [x] 4.2 Update `houmao-adv-usage-pattern` skill and pattern-page routing text so composed topology, mixed graph planning, multi-lane relay, rendered graph, policy authoring, and run-control route to `houmao-agent-loop-generic`.
- [x] 4.3 Update README system-skills table and auto-install/user-control prose to list `houmao-agent-loop-generic` instead of `houmao-agent-loop-relay`.
- [x] 4.4 Update `docs/getting-started/system-skills-overview.md` and `docs/reference/cli/system-skills.md` to describe `houmao-agent-loop-generic` and remove relay-only current-skill wording.
- [x] 4.5 Update any tests, fixtures, snapshots, or generated references that assert the packaged system-skill catalog contains `houmao-agent-loop-relay`.

## 5. Validation

- [x] 5.1 Run `openspec validate replace-relay-loop-with-generic-loop-planner --strict`.
- [x] 5.2 Run targeted text checks to ensure current source/docs no longer present `houmao-agent-loop-relay` as a current packaged skill outside archive/history/change-artifact contexts.
- [x] 5.3 Run the relevant system-skill catalog or packaging tests, or document why no narrower test exists.
- [x] 5.4 Run the relevant documentation or formatting checks for touched Markdown and catalog files, or document why they were skipped.
